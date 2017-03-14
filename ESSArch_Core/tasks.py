"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import errno
import os
import shutil
import urllib
import uuid

import requests

from requests_toolbelt import MultipartEncoder

from celery.result import allow_join_result

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.conf import settings

from ESSArch_Core.util import (
    alg_from_str,
)

from ESSArch_Core.essxml.Generator.xmlGenerator import (
    findElementWithoutNamespace,
    XMLGenerator
)
from ESSArch_Core.essxml.util import FILE_ELEMENTS, find_files
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep,
    ProcessTask,
)
from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.util import (
    creation_date,
    find_destination,
    getSchemas,
    get_value_from_path,
    remove_prefix,
    timestamp_to_datetime,
    win_to_posix,
)

from fido.fido import Fido
from lxml import etree


class CalculateChecksum(DBTask):
    queue = 'file_operation'

    def run(self, filename=None, block_size=65536, algorithm='SHA-256'):
        """
        Calculates the checksum for the given file, one chunk at a time

        Args:
            filename: The filename to calculate checksum for
            block_size: The size of the chunk to calculate
            algorithm: The algorithm to use

        Returns:
            The hexadecimal digest of the checksum
        """

        hash_val = alg_from_str(algorithm)()

        with open(filename, 'r') as f:
            while True:
                data = f.read(block_size)
                if data:
                    hash_val.update(data)
                else:
                    break

        return hash_val.hexdigest()

    def undo(self, filename=None, block_size=65536, algorithm='SHA-256'):
        pass

    def event_outcome_success(self, filename=None, block_size=65536, algorithm='SHA-256'):
        return "Created checksum for %s with %s" % (filename, algorithm)


class IdentifyFileFormat(DBTask):
    queue = 'file_operation'

    def handle_matches(self, fullname, matches, delta_t, matchtype=''):
        if len(matches) == 0:
            raise ValueError("No matches for %s" % fullname)

        f, sigName = matches[-1]
        self.lastFmt = f.find('name').text

    def run(self, filename=None, fid=Fido()):
        """
        Identifies the format of the file using the fido library

        Args:
            filename: The filename to identify

        Returns:
            The format of the file
        """

        self.fid = fid
        self.fid.handle_matches = self.handle_matches
        self.fid.identify_file(filename)

        return self.lastFmt

    def undo(self, filename=None, fid=Fido()):
        pass

    def event_outcome_success(self, filename=None, fid=Fido()):
        return "Identified format of %s" % filename


class ParseFile(DBTask):
    queue = 'file_operation'
    hidden = True

    def run(self, filepath=None, mimetype=None, relpath=None, algorithm='SHA-256'):
        if not relpath:
            relpath = filepath

        relpath = win_to_posix(relpath)

        timestamp = creation_date(filepath)
        createdate = timestamp_to_datetime(timestamp)

        checksum_task = ProcessTask(
            name="preingest.tasks.CalculateChecksum",
            params={
                "filename": filepath,
                "algorithm": algorithm
            },
            processstep_id=self.step,
            responsible_id=self.responsible,
            information_package_id=self.ip
        )

        fileformat_task = ProcessTask(
            name="preingest.tasks.IdentifyFileFormat",
            params={
                "filename": filepath,
            },
            processstep_id=self.step,
            responsible_id=self.responsible,
            information_package_id=self.ip
        )

        ProcessTask.objects.bulk_create([checksum_task, fileformat_task])

        checksum = checksum_task.run().get()
        self.set_progress(50, total=100)
        fileformat = fileformat_task.run().get()

        fileinfo = {
            'FName': os.path.basename(relpath),
            'FChecksum': checksum,
            'FID': str(uuid.uuid4()),
            'daotype': "borndigital",
            'href': relpath,
            'FMimetype': mimetype,
            'FCreated': createdate.isoformat(),
            'FFormatName': fileformat,
            'FSize': str(os.path.getsize(filepath)),
            'FUse': 'Datafile',
            'FChecksumType': algorithm,
            'FLoctype': 'URL',
            'FLinkType': 'simple',
            'FChecksumLib': 'hashlib',
            'FLocationType': 'URI',
            'FIDType': 'UUID',
        }

        return fileinfo

    def undo(self, filepath=None, mimetype=None, relpath=None, algorithm='SHA-256'):
        return ''

    def event_outcome_success(self, filepath=None, mimetype=None, relpath=None, algorithm='SHA-256'):
        return "Parsed file %s" % filepath


class GenerateXML(DBTask):
    def run(self, info={}, filesToCreate={}, folderToParse=None, algorithm='SHA-256'):
        """
        Generates the XML using the specified data and folder, and adds the XML
        to the specified files
        """

        generator = XMLGenerator(
            filesToCreate, info, self
        )

        generator.generate(
            folderToParse=folderToParse, algorithm=algorithm,
        )

    def undo(self, info={}, filesToCreate={}, folderToParse=None, algorithm='SHA-256'):
        for f, template in filesToCreate.iteritems():
            os.remove(f)

    def event_outcome_success(self, info={}, filesToCreate={}, folderToParse=None, algorithm='SHA-256'):
        return "Generated %s" % ", ".join(filesToCreate.keys())


class InsertXML(DBTask):
    """
    Inserts XML to the specifed file
    """

    def run(self, filename=None, elementToAppendTo=None, spec={}, info={}, index=None):
        generator = XMLGenerator()

        generator.insert(filename, elementToAppendTo, spec, info=info, index=index)

    def undo(self, filename=None, elementToAppendTo=None, spec={}, info={}, index=None):
        tree = etree.parse(filename)
        parent = findElementWithoutNamespace(tree, elementToAppendTo)

        found = parent.findall('.//{*}%s' % spec['-name'])

        if index is None or index >= len(parent):
            parent.remove(found[-1])
        else:
            parent.remove(parent[index])

        tree.write(filename, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def event_outcome_success(self, filename=None, elementToAppendTo=None, spec={}, info={}, index=None):
        return "Inserted XML to element %s in %s" % (elementToAppendTo, filename)


class AppendEvents(DBTask):
    def run(self, filename="", events={}):
        generator = XMLGenerator()
        template = {
            "-name": "event",
            "-min": 1,
            "-max": 1,
            "-allowEmpty": 1,
            "-namespace": "premis",
            "-children": [
                {
                    "-name": "eventIdentifier",
                    "-min": 1,
                    "-max": 1,
                    "-allowEmpty": 1,
                    "-namespace": "premis",
                    "-children": [
                        {
                            "-name": "eventIdentifierType",
                            "-min": 1,
                            "-max": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventIdentifierType"}]
                        }, {
                            "-name": "eventIdentifierValue",
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventIdentifierValue"}]
                        },
                    ]
                },
                {
                    "-name": "eventType",
                    "-min": 1,
                    "-max": 1,
                    "-allowEmpty": 1,
                    "-namespace": "premis",
                    "#content": [{"var": "eventType"}]
                },
                {
                    "-name": "eventDateTime",
                    "-min": 1,
                    "-max": 1,
                    "-allowEmpty": 1,
                    "-namespace": "premis",
                    "#content": [{"var": "eventDateTime"}]
                },
                {
                    "-name": "eventDetailInformation",
                    "-namespace": "premis",
                    "-children": [
                        {
                            "-name": "eventDetail",
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventDetail"}]
                        },
                    ]
                },
                {
                    "-name": "eventOutcomeInformation",
                    "-min": 1,
                    "-max": 1,
                    "-allowEmpty": 1,
                    "-namespace": "premis",
                    "-children": [
                        {
                            "-name": "eventOutcome",
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventOutcome"}]
                        },
                        {
                            "-name": "eventOutcomeDetail",
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "-children": [
                                {
                                    "-name": "eventOutcomeDetailNote",
                                    "-min": 1,
                                    "-max": 1,
                                    "-allowEmpty": 1,
                                    "-namespace": "premis",
                                    "#content": [{"var": "eventOutcomeDetailNote"}]
                                },
                            ]
                        },
                    ]
                },
                {
                    "-name": "linkingAgentIdentifier",
                    "-min": 1,
                    "-max": 1,
                    "-allowEmpty": 1,
                    "-namespace": "premis",
                    "-children": [
                        {
                            "-name": "linkingAgentIdentifierType",
                            "-min": 1,
                            "-max": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "linkingAgentIdentifierType"}]
                        },
                        {
                            "-name": "linkingAgentIdentifierValue",
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "linkingAgentIdentifierValue"}]
                        },
                    ]
                },
                {
                    "-name": "linkingObjectIdentifier",
                    "-min": 1,
                    "-max": 1,
                    "-allowEmpty": 1,
                    "-namespace": "premis",
                    "-children": [
                        {
                            "-name": "linkingObjectIdentifierType",
                            "-min": 1,
                            "-max": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "linkingObjectIdentifierType"}]
                        },
                        {
                            "-name": "linkingObjectIdentifierValue",
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "linkingObjectIdentifierValue"}]
                        },
                    ]
                },
            ]
        }

        if not events:
            events = EventIP.objects.filter(linkingObjectIdentifierValue_id=self.ip)

        events = events.order_by(
            'eventDateTime'
        )

        for event in events:
            data = {
                "eventIdentifierType": "SE/RA",
                "eventIdentifierValue": str(event.id),
                "eventType": str(event.eventType.eventType),
                "eventDateTime": str(event.eventDateTime),
                "eventDetail": event.eventType.eventDetail,
                "eventOutcome": str(event.eventOutcome),
                "eventOutcomeDetailNote": event.eventOutcomeDetailNote,
                "linkingAgentIdentifierType": "SE/RA",
                "linkingAgentIdentifierValue": event.linkingAgentIdentifierValue.username,
                "linkingObjectIdentifierType": "SE/RA",
                "linkingObjectIdentifierValue": str(event.linkingObjectIdentifierValue.ObjectIdentifierValue),
            }

            generator.insert(filename, "premis", template, data)

    def undo(self, filename="", events={}):
        tree = etree.parse(filename)
        parent = findElementWithoutNamespace(tree, 'premis')

        # Remove last |events| from parent
        for event_el in parent.findall('.//{*}event')[-len(events):]:
            parent.remove(event_el)

        tree.write(filename, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def event_outcome_success(self, filename="", events={}):
        return "Appended events to %s" % filename


class CopySchemas(DBTask):
    def findDestination(self, dirname, structure, path=''):
        for content in structure:
            if content['name'] == dirname and content['type'] == 'folder':
                return os.path.join(path, dirname)
            elif content['type'] == 'dir':
                rec = self.findDestination(
                    dirname, content['children'], os.path.join(path, content['name'])
                )
                if rec: return rec

    def createSrcAndDst(self, schema, root, structure):
        src = schema['location']
        fname = os.path.basename(src.rstrip("/"))
        dst = os.path.join(
            root,
            self.findDestination(schema['preservation_location'], structure),
            fname
        )

        return src, dst

    def run(self, schema={}, root=None, structure=None):
        """
        Copies the schema to a specified location
        """

        src, dst = self.createSrcAndDst(schema, root, structure)
        urllib.urlretrieve(src, dst)

    def undo(self, schema={}, root=None, structure=None):
        pass

    def event_outcome_success(self, schema={}, root=None, structure=None):
        src, dst = self.createSrcAndDst(schema, root, structure)
        return "Copied schemas from %s to %s" % src, dst


class ValidateFiles(DBTask):
    hidden = True
    fileformat_task = "ESSArch_Core.tasks.ValidateFileFormat"
    checksum_task = "ESSArch_Core.tasks.ValidateIntegrity"

    def run(self, ip=None, xmlfile=None, validate_fileformat=True, validate_integrity=True, rootdir=None):
        step = ProcessStep.objects.create(
            name="Validate Files",
            parallel=True,
            parent_step_id=self.step
        )

        if any([validate_fileformat, validate_integrity]):
            if rootdir is None:
                rootdir = InformationPackage.objects.values_list('ObjectPath', flat=True).get(pk=ip)

            doc = etree.ElementTree(file=xmlfile)
            tasks = []

            for elname, props in FILE_ELEMENTS.iteritems():
                for f in doc.xpath('.//*[local-name()="%s"]' % elname):
                    fpath = get_value_from_path(f, props["path"])

                    if fpath:
                        fpath = remove_prefix(fpath, props.get("pathprefix", ""))

                    fformat = get_value_from_path(f, props.get("format"))
                    checksum = get_value_from_path(f, props.get("checksum"))
                    algorithm = get_value_from_path(f, props.get("checksumtype"))

                    if validate_fileformat and fformat is not None:
                        tasks.append(ProcessTask(
                            name=self.fileformat_task,
                            params={
                                "filename": os.path.join(rootdir, fpath),
                                "fileformat": fformat,
                            },
                            information_package_id=ip,
                            responsible_id=self.responsible,
                            processstep=step,
                        ))

                    if validate_integrity and checksum is not None:
                        tasks.append(ProcessTask(
                            name=self.checksum_task,
                            params={
                                "filename": os.path.join(rootdir, fpath),
                                "checksum": checksum,
                                "algorithm": algorithm,
                            },
                            information_package_id=ip,
                            responsible_id=self.responsible,
                            processstep=step,
                        ))

            ProcessTask.objects.bulk_create(tasks)

        with allow_join_result():
            return step.run().get()

    def undo(self, ip=None, xmlfile=None, validate_fileformat=True, validate_integrity=True, rootdir=None):
        pass

    def event_outcome_success(self, ip, xmlfile, validate_fileformat=True, validate_integrity=True, rootdir=None):
        return "Validated files in %s" % xmlfile


class ValidateFileFormat(DBTask):
    queue = 'validation'

    def run(self, filename=None, fileformat=None):
        """
        Validates the format of the given file
        """

        task = ProcessTask.objects.values(
            'information_package_id', 'responsible_id'
        ).get(pk=self.request.id)

        t = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.IdentifyFileFormat",
            params={
                "filename": filename,
            },
            information_package_id=task.get('information_package_id'),
            responsible_id=task.get('responsible_id'),
        )

        res = t.run().get()

        assert res == fileformat, "fileformat for %s is not valid" % filename
        return "Success"

    def undo(self, filename=None, fileformat=None):
        pass

    def event_outcome_success(self, filename=None, fileformat=None):
        return "Validated format of %s to be %s" % (filename, fileformat)


class ValidateIntegrity(DBTask):
    queue = 'validation'

    def run(self, filename=None, checksum=None, block_size=65536, algorithm='SHA-256'):
        """
        Validates the integrity(checksum) for the given file
        """

        task = ProcessTask.objects.values(
            'information_package_id', 'responsible_id'
        ).get(pk=self.request.id)

        t = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CalculateChecksum",
            params={
                "filename": filename,
                "block_size": block_size,
                "algorithm": algorithm
            },
            information_package_id=task.get('information_package_id'),
            responsible_id=task.get('responsible_id'),
        )

        digest = t.run().get()

        assert digest == checksum, "checksum for %s is not valid (%s != %s)" % (filename, digest, checksum)
        return "Success"

    def undo(self, filename=None, checksum=None,  block_size=65536, algorithm='SHA-256'):
        pass

    def event_outcome_success(self, filename=None, checksum=None, block_size=65536, algorithm='SHA-256'):
        return "Validated integrity of %s against %s with %s" % (filename, checksum, algorithm)


class ValidateXMLFile(DBTask):
    queue = 'validation'

    def run(self, xml_filename=None, schema_filename=None):
        """
        Validates (using LXML) an XML file using a specified schema file
        """

        doc = etree.ElementTree(file=xml_filename)

        if schema_filename:
            xmlschema = etree.XMLSchema(etree.parse(schema_filename))
        else:
            xmlschema = getSchemas(doc=doc)

        xmlschema.assertValid(doc)
        return "Success"

    def undo(self, xml_filename=None, schema_filename=None):
        pass

    def event_outcome_success(self, xml_filename=None, schema_filename=None):
        return "Validated %s against schema" % xml_filename


class ValidateLogicalPhysicalRepresentation(DBTask):
    """
    Validates the logical and physical representation of objects.

    The comparison checks if the lists contains the same elements (though not
    the order of the elements).

    See http://stackoverflow.com/a/7829388/1523238
    """

    queue = 'validation'

    def run(self, dirname=None, files=[], files_reldir=None, xmlfile=None, rootdir=""):
        if dirname:
            xmlrelpath = os.path.relpath(xmlfile, dirname)
            xmlrelpath = remove_prefix(xmlrelpath, "./")
        else:
            xmlrelpath = xmlfile

        logical_files = find_files(xmlfile, rootdir)
        physical_files = set()

        if dirname:
            for root, dirs, filenames in os.walk(dirname):
                for f in filenames:
                    if f != xmlrelpath:
                        reldir = os.path.relpath(root, dirname)
                        relfile = os.path.join(reldir, f)
                        relfile = win_to_posix(relfile)
                        relfile = remove_prefix(relfile, "./")

                        physical_files.add(relfile)

        for f in files:
            if files_reldir:
                f = os.path.relpath(f, files_reldir)
            physical_files.add(f)

        assert logical_files == physical_files, "the logical representation differs from the physical"
        return "Success"

    def undo(self, dirname=None, files=[], files_reldir=None, xmlfile=None, rootdir=''):
        pass

    def event_outcome_success(self, dirname=None, files=[], files_reldir=None, xmlfile=None, rootdir=''):
        return "Validated logical and physical structure of %s and %s" % (xmlfile, dirname)


class UpdateIPStatus(DBTask):
    def run(self, ip=None, status=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(State=status)
    def undo(self, ip=None, status=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(State=prev)

    def event_outcome_success(self, ip=None, status=None, prev=None):
        return "Updated status of %s to %s" % (ip, status)


class UpdateIPPath(DBTask):
    def run(self, ip=None, path=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(ObjectPath=path)
    def undo(self, ip=None, path=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(ObjectPath=prev)

    def event_outcome_success(self, ip=None, path=None, prev=None):
        return "Updated path of %s to %s" % (ip, path)


class DeleteFiles(DBTask):
    def run(self, path=None):
        try:
            shutil.rmtree(path)
        except OSError as e:
            if e.errno == errno.ENOTDIR:
                try:
                    os.remove(path)
                except:
                    raise

    def undo(self, path=None):
        pass

    def event_outcome_success(self, path=None):
        return "Deleted %s" % path


class CopyChunk(DBTask):
    def local(self, src, dst, block_size=65536, offset=0):
        with open(src, 'r') as srcf, open(dst, 'a') as dstf:
            srcf.seek(offset)
            dstf.seek(offset)

            dstf.write(srcf.read(block_size))

    def remote(self, src, dst, requests_session, block_size=65536, offset=0, file_size=0):
        with open(src, 'rb') as srcf:
            srcf.seek(offset)

            filename = os.path.basename(src)
            chunk = srcf.read(block_size)

            HTTP_CONTENT_RANGE = 'bytes %s-%s/%s' % (offset, offset+block_size-1, file_size)

            data = MultipartEncoder(fields=(('chunk', chunk), ('filename', filename)))
            headers = {
                'Content-Type': data.content_type,
                'Content-Range': HTTP_CONTENT_RANGE
            }

            response = requests.post(dst, data=data, headers=headers)

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise ValueError(e.args[0])

    def run(self, src=None, dst=None, requests_session=None, offset=0, block_size=65536, file_size=0):
        """
        Copies the given chunk to the given destination

        Args:
            src: The file to copy
            dst: Where the file should be copied to
            requests_session: The session to be used
            offset: The offset in the file
            block_size: Size of each block to copy
        Returns:
            None
        """

        val = URLValidator(dst)

        try:
            val(dst)
            self.remote(src, dst, requests_session, block_size, offset, file_size)
        except ValidationError:
            self.local(src, dst, block_size, offset)

    def undo(self, src=None, dst=None, requests_session=None, offset=0, block_size=65536, file_size=0):
        pass

    def event_outcome_success(self, src=None, dst=None, requests_session=None, offset=0, block_size=65536, file_size=0):
        return "Copied chunk at offset %s and size %s from %s to %s" % (offset, block_size, src, dst)


class CopyFile(DBTask):
    def local(self, src, dst, block_size=65536, step=None):
        step = ProcessStep.objects.create(
            name="Copy %s to %s" % (src, dst),
            parent_step_id=step
        )

        fsize = os.stat(src).st_size
        idx = 0

        tasks = []

        open(dst, 'w').close()  # remove content of destination if it exists

        while idx*block_size <= fsize:
            tasks.append(ProcessTask(
                name="ESSArch_Core.tasks.CopyChunk",
                params={
                    'src': src,
                    'dst': dst,
                    'offset': idx*block_size,
                    'block_size': block_size
                },
                processstep=step,
                processstep_pos=idx,
            ))
            idx += 1

        ProcessTask.objects.bulk_create(tasks)

        step.run().get()

    def remote(self, src, dst, requests_session=None, block_size=65536, step=None):
        step = ProcessStep.objects.create(
            name="Copy %s to %s" % (src, dst),
            parent_step_id=step
        )

        file_size = os.stat(src).st_size
        idx = 0

        tasks = []

        while idx*block_size <= file_size:
            tasks.append(ProcessTask(
                name="ESSArch_Core.tasks.CopyChunk",
                params={
                    'src': src,
                    'dst': dst,
                    'requests_session': requests_session,
                    'offset': idx*block_size,
                    'block_size': block_size,
                    'file_size': file_size
                },
                processstep=step,
                processstep_pos=idx,
            ))
            idx += 1

        ProcessTask.objects.bulk_create(tasks)

        step.run().get()

    def run(self, src=None, dst=None, requests_session=None, block_size=65536):
        """
        Copies the given file to the given destination

        Args:
            src: The file to copy
            dst: Where the file should be copied to
            requests_session: The request session to be used
            block_size: Size of each block to copy
        Returns:
            None
        """

        if dst is None:
            raise ValueError

        val = URLValidator(dst)
        step = ProcessTask.objects.values_list('processstep', flat=True).get(pk=self.request.id)

        try:
            val(dst)
            self.remote(src, dst, requests_session, block_size, step)
        except ValidationError:
            self.local(src, dst, block_size, step)

    def undo(self, src=None, dst=None, requests_session=None, block_size=65536):
        pass

    def event_outcome_success(self, src=None, dst=None, requests_session=None, block_size=65536):
        return "Copied %s to %s" % (src, dst)


class SendEmail(DBTask):
    def run(self, sender=None, recipients=[], subject=None, body=None, attachments=[]):
        email = EmailMessage(
            subject,
            body,
            sender,
            recipients,
        )

        for a in attachments:
            email.attach_file(a)

        email.send()

    def undo(self, sender=None, recipients=[], subject=None, body=None, attachments=[]):
        pass

    def event_outcome_success(self, sender=None, recipients=[], subject=None, body=None, attachments=[]):
        pass


class DownloadSchemas(DBTask):
    def run(self, template=None, dirname=None, structure=[], root=""):
        schemaPreserveLoc = template.get('-schemaPreservationLocation')

        if schemaPreserveLoc and structure:
            dirname, _ = find_destination(
                schemaPreserveLoc, structure
            )
            dirname = os.path.join(root, dirname)

        for schema in template.get('-schemasToPreserve', []):
            dst = os.path.join(dirname, os.path.basename(schema))

            t = ProcessTask.objects.create(
                name="ESSArch_Core.tasks.DownloadFile",
                params={'src': schema, 'dst': dst},
                processstep_id=self.step,
                processstep_pos=self.step_pos,
                responsible_id=self.responsible,
                information_package_id=self.ip,
            )

            t.run().get()

    def undo(self, template=None, dirname=None, structure=[], root="", task=None):
        pass

    def event_outcome_success(self, template=None, dirname=None, structure=[], root="", task=None):
        pass


class DownloadFile(DBTask):
    def run(self, src=None, dst=None):
        r = requests.get(src, stream=True)
        if r.status_code == 200:
            with open(dst, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

    def undo(self, src=None, dst=None):
        pass

    def event_outcome_success(self, src=None, dst=None):
        pass
