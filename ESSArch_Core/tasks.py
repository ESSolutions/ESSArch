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
import tarfile
import urllib
import uuid
import zipfile

import requests

from requests_toolbelt import MultipartEncoder

from celery.result import allow_join_result

from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models import F

from ESSArch_Core.util import (
    alg_from_str,
    convert_file,
    get_tree_size_and_count,
)

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.Generator.xmlGenerator import (
    findElementWithoutNamespace,
    XMLGenerator
)
from ESSArch_Core.essxml.util import FILE_ELEMENTS, find_files, find_pointers, validate_against_schema
from ESSArch_Core.ip.models import EventIP, InformationPackage
from ESSArch_Core.storage.models import StorageMedium, TapeDrive
from ESSArch_Core.storage.tape import (
    DEFAULT_TAPE_BLOCK_SIZE,

    create_tape_label,
    get_tape_file_number,
    is_tape_drive_online,
    mount_tape,
    read_tape,
    rewind_tape,
    set_tape_file_number,
    tape_empty,
    unmount_tape,
    verify_tape_label,
    wait_to_come_online,
    write_to_tape,
)
from ESSArch_Core.WorkflowEngine.models import (
    ProcessStep,
    ProcessTask,
)
from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.util import (
    creation_date,
    find_destination,
    get_value_from_path,
    remove_prefix,
    timestamp_to_datetime,
    win_to_posix,
)

from fido.fido import Fido
from lxml import etree
from scandir import walk


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

        try:
            self.format_name = f.find('name').text
        except AttributeError:
            self.format_name = None

        try:
            self.format_version = f.find('version').text
        except AttributeError:
            self.format_version = None

        try:
            self.format_registry_key = f.find('puid').text
        except AttributeError:
            self.format_registry_key = None

    def run(self, filename=None, fid=Fido()):
        """
        Identifies the format of the file using the fido library

        Args:
            filename: The filename to identify

        Returns:
            A tuple with the format name, version and registry key
        """

        self.fid = fid
        self.fid.handle_matches = self.handle_matches
        self.fid.identify_file(filename)

        return (self.format_name, self.format_version, self.format_registry_key)

    def undo(self, filename=None, fid=Fido()):
        pass

    def event_outcome_success(self, filename=None, fid=Fido()):
        return "Identified format of %s" % filename


class ParseFile(DBTask):
    queue = 'file_operation'
    hidden = True

    def run(self, filepath=None, mimetype=None, relpath=None, algorithm='SHA-256', rootdir=''):
        if not relpath:
            relpath = filepath

        relpath = win_to_posix(relpath)

        timestamp = creation_date(filepath)
        createdate = timestamp_to_datetime(timestamp)

        checksum_task = ProcessTask(
            name="ESSArch_Core.tasks.CalculateChecksum",
            params={
                "filename": filepath,
                "algorithm": algorithm
            },
            processstep_id=self.step,
            responsible_id=self.responsible,
            information_package_id=self.ip
        )

        fileformat_task = ProcessTask(
            name="ESSArch_Core.tasks.IdentifyFileFormat",
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
        (format_name, format_version, format_registry_key) = fileformat_task.run().get()

        fileinfo = {
            'FName': os.path.basename(relpath),
            'FDir': rootdir,
            'FChecksum': checksum,
            'FID': str(uuid.uuid4()),
            'daotype': "borndigital",
            'href': relpath,
            'FMimetype': mimetype,
            'FCreated': createdate.isoformat(),
            'FFormatName': format_name,
            'FFormatVersion': format_version,
            'FFormatRegistryKey': format_registry_key,
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

    def undo(self, filepath=None, mimetype=None, relpath=None, algorithm='SHA-256', rootdir=''):
        return ''

    def event_outcome_success(self, filepath=None, mimetype=None, relpath=None, algorithm='SHA-256', rootdir=''):
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
            try:
                os.remove(f)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

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
                "linkingObjectIdentifierValue": str(event.linkingObjectIdentifierValue.object_identifier_value),
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


class CreateTAR(DBTask):
    """
    Creates a TAR file from the specified directory

    Args:
        dirname: The directory to create a TAR from
        tarname: The name of the tar file
    """

    def run(self, dirname=None, tarname=None, compress=False):
        compression = ':gz' if compress else ''
        base_dir = os.path.basename(os.path.normpath(dirname))
        with tarfile.open(tarname, 'w%s' % compression) as new_tar:
            new_tar.add(dirname, base_dir)

        self.set_progress(100, total=100)
        return tarname

    def undo(self, dirname=None, tarname=None, compress=False):
        parent_dir = os.path.dirname((os.path.normpath(dirname)))

        with tarfile.open(tarname, 'r') as tar:
            tar.extractall(parent_dir)

        os.remove(tarname)

    def event_outcome_success(self, dirname=None, tarname=None, compress=False):
        return "Created %s from %s" % (tarname, dirname)


class CreateZIP(DBTask):
    """
    Creates a ZIP file from the specified directory

    Args:
        dirname: The directory to create a ZIP from
        zipname: The name of the zip file
    """

    def run(self, dirname=None, zipname=None, compress=False):
        compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
        with zipfile.ZipFile(zipname, 'w', compression) as new_zip:
            for root, dirs, files in walk(dirname):
                for d in dirs:
                    filepath = os.path.join(root, d)
                    arcname = os.path.relpath(filepath, dirname)
                    new_zip.write(filepath, arcname)
                for f in files:
                    filepath = os.path.join(root, f)
                    arcname = os.path.relpath(filepath, dirname)
                    new_zip.write(filepath, arcname)

        self.set_progress(100, total=100)
        return zipname

    def undo(self, dirname=None, zipname=None, compress=False):
        with zipfile.ZipFile(zipname, 'r') as z:
            z.extractall(dirname)

        os.remove(zipname)

    def event_outcome_success(self, dirname=None, zipname=None, compress=False):
        return "Created %s from %s" % (zipname, dirname)


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
                rootdir = InformationPackage.objects.values_list('object_path', flat=True).get(pk=ip)

            tasks = []

            for f in find_files(xmlfile, rootdir):
                if validate_fileformat and f.format is not None:
                    tasks.append(ProcessTask(
                        name=self.fileformat_task,
                        params={
                            "filename": os.path.join(rootdir, f.path),
                            "format_name": f.format,
                        },
                        information_package_id=ip,
                        responsible_id=self.responsible,
                        processstep=step,
                    ))

                if validate_integrity and f.checksum is not None and f.checksum_type is not None:
                    tasks.append(ProcessTask(
                        name=self.checksum_task,
                        params={
                            "filename": os.path.join(rootdir, f.path),
                            "checksum": f.checksum,
                            "algorithm": f.checksum_type,
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

    def run(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
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

        actual_format_name, actual_format_version, actual_format_registry_key = t.run().get()

        if format_name:
            assert actual_format_name == format_name, "format name for %s is not valid, (%s != %s)" % (filename, format_name, actual_format_name)

        if format_version:
            assert actual_format_version == format_version, "format version for %s is not valid" % filename

        if format_registry_key:
            assert actual_format_registry_key == format_registry_key, "format registry key for %s is not valid" % filename

        return "Success"

    def undo(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
        pass

    def event_outcome_success(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
        return "Validated format of %s to be: format name: %s, format version: %s, format registry key: %s" % (
            filename, format_name, format_version, format_registry_key
        )


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

    def run(self, xml_filename=None, schema_filename=None, rootdir=None):
        """
        Validates (using LXML) an XML file using a specified schema file
        """

        assert validate_against_schema(xmlfile=xml_filename, schema=schema_filename, rootdir=rootdir)
        return "Success"

    def undo(self, xml_filename=None, schema_filename=None, rootdir=None):
        pass

    def event_outcome_success(self, xml_filename=None, schema_filename=None, rootdir=None):
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
            for root, dirs, filenames in walk(dirname):
                for f in filenames:
                    reldir = os.path.relpath(root, dirname)
                    relfile = os.path.join(reldir, f)
                    relfile = win_to_posix(relfile)
                    relfile = remove_prefix(relfile, "./")

                    if relfile != xmlrelpath:
                        physical_files.add(relfile)

        for f in files:
            if files_reldir:
                if f == files_reldir:
                    physical_files.add(os.path.basename(f))
                    continue

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
        InformationPackage.objects.filter(pk=ip).update(state=status)
    def undo(self, ip=None, status=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(state=prev)

    def event_outcome_success(self, ip=None, status=None, prev=None):
        return "Updated status of %s to %s" % (ip, status)


class UpdateIPPath(DBTask):
    def run(self, ip=None, path=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(object_path=path)
    def undo(self, ip=None, path=None, prev=None):
        InformationPackage.objects.filter(pk=ip).update(object_path=prev)

    def event_outcome_success(self, ip=None, path=None, prev=None):
        return "Updated path of %s to %s" % (ip, path)


class UpdateIPSizeAndCount(DBTask):
    queue = 'file_operation'

    def run(self, ip=None):
        path = InformationPackage.objects.values_list('object_path', flat=True).get(pk=ip)
        size, count = get_tree_size_and_count(path)

        InformationPackage.objects.filter(pk=ip).update(
            object_size=size, object_num_items=count
        )

        return size, count

    def undo(self, ip=None):
        pass

    def event_outcome_success(self, ip=None):
        return "Updated size and count of %s" % ip


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
    def local(self, src, dst, offset, block_size=65536):
        with open(src, 'r') as srcf, open(dst, 'a') as dstf:
            srcf.seek(offset)
            dstf.seek(offset)

            dstf.write(srcf.read(block_size))

    def remote(self, src, dst, offset, file_size, requests_session, upload_id=None, block_size=65536):
        filename = os.path.basename(src)

        with open(src, 'rb') as srcf:
            srcf.seek(offset)
            chunk = srcf.read(block_size)

        start = offset
        end = offset + block_size - 1

        if end > file_size:
            end = file_size - 1

        HTTP_CONTENT_RANGE = 'bytes %s-%s/%s' % (start, end, file_size)
        headers = {'Content-Range': HTTP_CONTENT_RANGE}

        data = {'upload_id': upload_id}
        files = {'the_file': (filename, chunk)}
        response = requests_session.post(dst, data=data, files=files, headers=headers)
        response.raise_for_status()

        return response.json()['upload_id']

    def run(self, src, dst, offset, upload_id=None, file_size=None, requests_session=None, block_size=65536):
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

        if requests_session is not None:
            if file_size is None:
                raise ValueError('file_size required on remote transfers')

            return self.remote(src, dst, offset, file_size, requests_session, upload_id, block_size)
        else:
            self.local(src, dst, offset, block_size)

    def undo(self, src, dst, offset, upload_id=None, file_size=None, requests_session=None, block_size=65536):
        pass

    def event_outcome_success(self, src, dst, offset, upload_id, file_size=None, requests_session=None, block_size=65536):
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

        directory = os.path.dirname(dst)

        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        open(dst, 'w').close()  # remove content of destination if it exists

        while idx*block_size <= fsize:
            tasks.append(ProcessTask(
                name="ESSArch_Core.tasks.CopyChunk",
                args=[src, dst, idx*block_size, self.task_id],
                params={'block_size': block_size},
                processstep=step,
                processstep_pos=idx,
            ))
            idx += 1

        ProcessTask.objects.bulk_create(tasks, 1000)

        step.run().get()

    def remote(self, src, dst, requests_session=None, block_size=65536, step=None):
        step = ProcessStep.objects.create(
            name="Copy %s to %s" % (src, dst),
            parent_step_id=step
        )

        file_size = os.stat(src).st_size
        idx = 0

        tasks = []

        t = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CopyChunk",
            args=[src, dst, idx*block_size],
            params={
                'requests_session': requests_session,
                'file_size': file_size,
                'block_size': block_size,
            },
            processstep=step,
            processstep_pos=idx,
        )
        upload_id = t.run().get()
        idx += 1

        while idx*block_size <= file_size:
            tasks.append(ProcessTask(
                name="ESSArch_Core.tasks.CopyChunk",
                args=[src, dst, idx*block_size],
                params={
                    'requests_session': requests_session,
                    'file_size': file_size,
                    'block_size': block_size,
                    'upload_id': upload_id,
                },
                processstep=step,
                processstep_pos=idx,
            ))
            idx += 1

        ProcessTask.objects.bulk_create(tasks, 1000)

        step.resume().get()

        md5 = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.CalculateChecksum",
            params={
                "filename": src,
                "block_size": block_size,
                "algorithm": 'MD5'
            },
            information_package_id=self.ip,
            responsible_id=self.responsible,
        ).run().get()

        completion_url = dst.rstrip('/') + '_complete/'

        m = MultipartEncoder(
            fields={
                'path': os.path.basename(src),
                'upload_id': upload_id,
                'md5': md5,
            }
        )
        headers = {'Content-Type': m.content_type}

        response = requests_session.post(completion_url, data=m, headers=headers)
        response.raise_for_status()

    def run(self, src, dst, requests_session=None, block_size=65536):
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

        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        step = ProcessTask.objects.values_list('processstep', flat=True).get(pk=self.request.id)

        if requests_session is not None:
            self.remote(src, dst, requests_session, block_size, step)
        else:
            self.local(src, dst, block_size, step)

    def undo(self, src, dst, requests_session=None, block_size=65536):
        pass

    def event_outcome_success(self, src, dst, requests_session=None, block_size=65536):
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
        r = requests.get(src, stream=True, verify=False)
        r.raise_for_status()
        if r.status_code == 200:
            with open(dst, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

    def undo(self, src=None, dst=None):
        pass

    def event_outcome_success(self, src=None, dst=None):
        pass


class MountTape(DBTask):
    def run(self, medium=None, drive=None, timeout=120):
        """
        Mounts tape into drive

        Args:
            medium: Which medium to mount
            drive: Which drive to load to
        """

        medium = StorageMedium.objects.get(pk=medium)
        slot = medium.tape_slot.slot_id
        tape_drive = TapeDrive.objects.get(pk=drive)

        tape_drive.locked = True
        tape_drive.save(update_fields=['locked'])

        mount_tape(tape_drive.robot.device, slot, drive)

        wait_to_come_online(tape_drive.device, timeout)

        if medium.format not in [100, 101]:
            label_root = Path.objects.get(entity='label').value
            xmlpath = os.path.join(label_root, '%s_label.xml' % medium.medium_id)

            if tape_empty(tape_drive.device):
                create_tape_label(medium, xmlpath)
                rewind_tape(tape_drive.device)
                write_to_tape(tape_drive.device, xmlpath)
            else:
                tar = tarfile.open(tape_drive.device, 'r|')
                first_member = tar.getmembers()[0]

                if first_member.name.endswith('_label.xml'):
                    xmlstring = tar.extractfile(first_member).read()
                    tar.close()
                    if not verify_tape_label(medium, xmlstring):
                        raise ValueError('Tape contains labelfile with wrong tapeid')
                elif first_member.name == 'reuse':
                    tar.close()

                    create_tape_label(medium, xmlpath)
                    rewind_tape(tape_drive.device)
                    write_to_tape(tape_drive.device, xmlpath)
                else:
                    raise ValueError('Tape contains unknown information')

        TapeDrive.objects.filter(pk=drive).update(
            num_of_mounts=F('num_of_mounts')+1,
            locked=False,
        )
        StorageMedium.objects.filter(pk=medium.pk).update(
            num_of_mounts=F('num_of_mounts')+1,
            tape_drive_id=drive
        )

    def undo(self, robot=None, slot=None, drive=None):
        pass

    def event_outcome_success(self, robot=None, slot=None, drive=None):
        pass


class UnmountTape(DBTask):
    def run(self, drive=None):
        """
        Unmounts tape from drive into slot

        Args:
            drive: Which drive to unmount from
        """

        tape_drive = TapeDrive.objects.get(pk=drive)

        if not hasattr(tape_drive, 'storage_medium'):
            raise ValueError("No tape in tape drive to unmount")

        slot = tape_drive.storage_medium.tape_slot
        robot = tape_drive.robot

        tape_drive.locked = True
        tape_drive.save(update_fields=['locked'])

        res = unmount_tape(robot.device, slot.slot_id, tape_drive.pk)

        StorageMedium.objects.filter(pk=tape_drive.storage_medium.pk).update(
            tape_drive=None
        )

        tape_drive.locked = False
        tape_drive.save(update_fields=['locked'])

        return res


    def undo(self, robot=None, slot=None, drive=None):
        pass

    def event_outcome_success(self, robot=None, slot=None, drive=None):
        pass


class RewindTape(DBTask):
    def run(self, medium=None):
        """
        Rewinds the given tape
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return rewind_tape(drive.device)

    def undo(self, medium=None):
        pass

    def event_outcome_success(self, medium=None):
        pass


class IsTapeDriveOnline(DBTask):
    def run(self, drive=None):
        """
        Checks if the given tape drive is online

        Args:
            drive: Which drive to check

        Returns:
            True if the drive is online, false otherwise
        """

        return is_tape_drive_online(drive)

    def undo(self, drive=None):
        pass

    def event_outcome_success(self, drive=None):
        pass


class ReadTape(DBTask):
    def run(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        """
        Reads the tape in the given drive
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return read_tape(drive.device, path=path, block_size=block_size)

    def undo(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass

    def event_outcome_success(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass


class WriteToTape(DBTask):
    def run(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        """
        Writes content to a tape drive
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return write_to_tape(drive.device, path=path, block_size=block_size)

    def undo(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass

    def event_outcome_success(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass


class GetTapeFileNumber(DBTask):
    def run(self, medium=None):
        """
        Gets the current file number (position) of the given tape
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return get_tape_file_number(drive.device)

    def undo(self, medium=None):
        pass

    def event_outcome_success(self, medium=None):
        pass


class SetTapeFileNumber(DBTask):
    def run(self, medium=None, num=0):
        """
        Sets the current file number (position) of the given tape
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return set_tape_file_number(drive.device, num)

    def undo(self, medium=None, num=0):
        pass

    def event_outcome_success(self, medium=None, num=0):
        pass

class ConvertFile(DBTask):
    def run(self, filepath, new_format, delete_original=True):
        try:
            convert_file(filepath, new_format)
        except:
            raise
        else:
            if delete_original:
                os.remove(filepath)

    def undo(self, filepath, new_format):
        pass

    def event_outcome_success(self, filepath, new_format):
        pass
