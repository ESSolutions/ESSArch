from __future__ import absolute_import

import hashlib, os, shutil, tarfile, urllib, zipfile

from django.conf import settings

from demo.xmlGenerator import createXML, appendXML

from fido.fido import Fido

from lxml import etree

from configuration.models import Path
from preingest.dbtask import DBTask
from ip.models import InformationPackage
from preingest.models import ProcessStep, ProcessTask

from preingest.util import getSchemas

class PrepareIP(DBTask):
    event_type = 10100

    def run(self, label="", responsible={}, step=None):
        """
        Prepares a new information package

        Args:
            label: The label of the IP to prepare
            responsible: The responsible user of the IP to prepare
            step: The step to connect the IP to

        Returns:
            The id of the created information package
        """


        ip = InformationPackage.objects.create(
            Label=label,
            Responsible=responsible,
            State="PREPARING",
            OAIStype="SIP",
        )

        prepare_path = Path.objects.get(
            entity="path_preingest_prepare"
        ).value

        ip.objectPath = os.path.join(
            prepare_path,
            str(ip.pk)
        )
        ip.save()

        self.taskobj.information_package = ip
        self.taskobj.save()

        if step is not None:
            s = ProcessStep.objects.get(pk=step)
            ip.steps.add(s)

        self.set_progress(100, total=100)

        return ip

    def undo(self, label="", responsible={}, step=None):
        pass


class CreateIPRootDir(DBTask):
    event_type = 10110

    def create_path(self, information_package_id):
        prepare_path = Path.objects.get(
            entity="path_preingest_prepare"
        ).value

        return os.path.join(
            prepare_path,
            str(information_package_id)
        )

    def run(self, information_package=None):
        """
        Creates the IP root directory

        Args:
            information_package_id: The id of the information package the
            directory will be created for

        Returns:
            None
        """

        self.taskobj.information_package = information_package
        self.taskobj.save()

        path = self.create_path(str(information_package.pk))
        os.makedirs(path)

        information_package.ObjectPath = path
        information_package.save()

        self.set_progress(100, total=100)
        return information_package

    def undo(self, information_package=None):
        path = self.create_path(information_package.pk)
        shutil.rmtree(path)


class CreatePhysicalModel(DBTask):
    event_type = 10115

    def run(self, structure={}, root=""):
        """
        Creates the IP physical model based on a logical model.

        Args:
            structure: A dict specifying the logical model.
            root: The root dictionary to be used
        """

        root = os.path.join(settings.BASE_DIR, str(root))

        for k, v in structure.iteritems():
            if v.get('type') == 'dir':
                k = str(k)
                dirname = os.path.join(root, k)
                os.makedirs(dirname)

                if 'children' in v:
                    self.run(v['children'], dirname)

        self.set_progress(1, total=1)

    def undo(self, structure={}, root=""):
        root = os.path.join(settings.BASE_DIR, str(root))

        if root:
            shutil.rmtree(root)
            return

        for k, v in structure.iteritems():
            k = str(k)
            dirname = os.path.join(root, k)
            shutil.rmtree(dirname)


class CalculateChecksum(DBTask):
    event_type = 10200

    def run(self, filename=None, block_size=65536, algorithm=hashlib.sha256):
        """
        Calculates the checksum for the given file, one chunk at a time

        Args:
            filename: The filename to calculate checksum for
            block_size: The size of the chunk to calculate
            algorithm: The algorithm to use

        Returns:
            The hexadecimal digest of the checksum
        """

        hash_val = algorithm()

        with open(filename, 'r') as f:
            while True:
                data = f.read(block_size)
                if data:
                    hash_val.update(data)
                else:
                    break

        self.set_progress(100, total=100)
        return hash_val.hexdigest()

    def undo(self, filename=None, block_size=65536, algorithm=hashlib.sha256):
        pass

    def get_event_args(self, filename=None, block_size=65536, algorithm=hashlib.sha256):
        return [filename]

class IdentifyFileFormat(DBTask):
    event_type = 10220

    def handle_matches(self, fullname, matches, delta_t, matchtype=''):
        f, sigName = matches[-1]
        self.lastFmt = f.find('name').text

    def run(self, filename=None):
        """
        Identifies the format of the file using the fido library

        Args:
            filename: The filename to identify

        Returns:
            The format of the file
        """

        self.fid = Fido()
        self.fid.handle_matches = self.handle_matches
        self.fid.identify_file(filename)

        self.set_progress(100, total=100)

        return self.lastFmt

    def undo(self, filename=None):
        pass

    def get_event_args(self, filename=None):
        return [filename]

class GenerateXML(DBTask):
    event_type = 10230

    """
    Generates the XML using the specified data and folder, and adds the XML to
    the specified files
    """

    def run(self, info={}, filesToCreate={}, folderToParse=None):
        createXML(info, filesToCreate, folderToParse)

        self.set_progress(100, total=100)

    def undo(self, info={}, filesToCreate={}, folderToParse=None):
        for f, template in filesToCreate.iteritems():
            os.remove(f)

    def get_event_args(self, info={}, filesToCreate={}, folderToParse=None):
        return [", ".join(filesToCreate.keys())]

class AppendEvents(DBTask):
    event_type = 10240

    """
    """

    def run(self, filename="", events={}):
        for event in events:
            inputD = {
                "path": filename,
                "elementToAppendTo": "premis:premis",
                "template": {
                    "event": {
                        "-min": 1,
                        "-max": 1,
                        "-allowEmpty": 1,
                        "-namespace": "premis",
                        "eventIdentifier": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "eventIdentifierType": {
                                "-min": 1,
                                "-max": 1,
                                "-namespace": "premis",
                                "#content": [{"var":"eventIdentifierType"}]
                            },
                            "eventIdentifierValue": {
                                "-min": 1,
                                "-max": 1,
                                "-allowEmpty": 1,
                                "-namespace": "premis",
                                "#content": [{"var": "eventIdentifierValue"}]
                            },
                        },
                        "eventType": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventType"}]
                        },
                        "eventDateTime": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventDateTime"}]
                        },
                        "eventDetail": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "#content": [{"var": "eventDetail"}]
                        },
                        "eventOutcomeInformation": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "eventOutcome": {
                                "-min": 1,
                                "-max": 1,
                                "-allowEmpty": 1,
                                "-namespace": "premis",
                                "#content": [{"var":"eventOutcome"}]
                            },
                            "eventOutcomeDetail": {
                                "-min": 1,
                                "-max": 1,
                                "-allowEmpty": 1,
                                "-namespace": "premis",
                                "eventOutcomeDetailNote": {
                                    "-min": 1,
                                    "-max": 1,
                                    "-allowEmpty": 1,
                                    "-namespace": "premis",
                                    "#content": [{"var":"eventOutcomeDetailNote"}]
                                },
                            },
                        },
                        "linkingAgentIdentifier": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "linkingAgentIdentifierType": {
                                "-min": 1,
                                "-max": 1,
                                "-namespace": "premis",
                                "#content": [{"var":"linkingAgentIdentifierType"}]
                            },
                            "linkingAgentIdentifierValue": {
                                "-min": 1,
                                "-max": 1,
                                "-allowEmpty": 1,
                                "-namespace": "premis",
                                "#content": [{"var": "linkingAgentIdentifierValue"}]
                            },
                        },
                        "linkingObjectIdentifier": {
                            "-min": 1,
                            "-max": 1,
                            "-allowEmpty": 1,
                            "-namespace": "premis",
                            "linkingObjectIdentifierType": {
                                "-min": 1,
                                "-max": 1,
                                "-namespace": "premis",
                                "#content": [{"var":"linkingObjectIdentifierType"}]
                            },
                            "linkingObjectIdentifierValue": {
                                "-min": 1,
                                "-max": 1,
                                "-allowEmpty": 1,
                                "-namespace": "premis",
                                "#content": [{"var": "linkingObjectIdentifierValue"}]
                            },
                        },
                    }
                },
                "data": {
                    "eventIdentifierType": "SE/RA",
                    "eventIdentifierValue": str(event.id),
                    "eventType": str(event.eventType.eventType),
                    "eventDateTime": str(event.eventDateTime),
                    "eventDetail": event.eventDetail,
                    "eventOutcome": event.eventOutcome,
                    "eventOutcomeDetailNote": event.eventOutcomeDetailNote,
                    "linkingAgentIdentifierType": "SE/RA",
                    "linkingAgentIdentifierValue": "admin",
                    "linkingObjectIdentifierType": "SE/RA",
                    "linkingObjectIdentifierValue": str(event.linkingObjectIdentifierValue.id),
                }
            }

            appendXML(inputD)
        self.set_progress(100, total=100)

    def undo(self, filename="", events={}):
        pass

    def get_event_args(self, filename="", events={}):
        return [filename]

class CopySchemas(DBTask):
    event_type = 10250

    """
    Copies the schema to a specified (?) location
    """

    def findDestination(self, dirname, structure, path=''):
        for k, v in structure.iteritems():
            if k == dirname and v.get('type') == 'dir':
                return os.path.join(path, dirname)
            elif v.get('type') == 'dir':
                rec = self.findDestination(
                    dirname, v['children'], os.path.join(path, k)
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

        src, dst = self.createSrcAndDst(schema, root, structure)
        urllib.urlretrieve(src, dst)

        self.set_progress(100, total=100)

    def undo(self, schema={}, root=None, structure=None):
        pass

    def get_event_args(self, schema={}, root=None, structure=None):
        src, dst = self.createSrcAndDst(schema, root, structure)
        return [src, dst]


class ValidateFiles(DBTask):
    def run(self, ip, mets_path):
        metsdoc = etree.ElementTree(file=mets_path)

        root = metsdoc.getroot()
        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}

        prepare_path = Path.objects.get(
            entity="path_preingest_prepare"
        ).value
        ip_prepare_path = os.path.join(prepare_path, str(ip.pk))

        step = ProcessStep.objects.create(
            name="Validate Files",
            parallel=True,
            parent_step=self.taskobj.processstep
        )

        for f in metsdoc.findall('.//mets:file', nsmap):
            filename = f.find('mets:FLocat', nsmap).get('{%s}href' % nsmap['xlink'])
            filename = os.path.join(ip_prepare_path, filename)
            fileformat = f.get("{%s}FILEFORMATNAME" % nsmap['ext'])
            checksum = f.get("CHECKSUM")

            step.tasks.add(ProcessTask.objects.create(
                name="preingest.tasks.ValidateFileFormat",
                params={
                    "filename": filename,
                    "fileformat": fileformat,
                },
                information_package=ip
            ))

            step.tasks.add(ProcessTask.objects.create(
                name="preingest.tasks.ValidateIntegrity",
                params={
                    "filename": filename,
                    "checksum": checksum,
                },
                information_package=ip
            ))


        self.set_progress(100, total=100)

        step.run()

    def undo(self, ip, mets_path):
        pass

class ValidateFileFormat(DBTask):
    event_type = 10260

    """
    Validates the format (PREFORMA, jhove, droid, etc.) of the given file
    """

    def run(self, filename=None, fileformat=None):
        self.set_progress(100, total=100)

    def undo(self, filename=None, fileformat=None):
        pass

    def get_event_args(self, filename=None, fileformat=None):
        return [filename, fileformat]


class ValidateXMLFile(DBTask):
    event_type = 10261

    """
    Validates (using LXML) an XML file using a specified schema file
    """

    def run(self, xml_filename=None, schema_filename=None):
        try:
            doc = etree.ElementTree(file=xml_filename)
        except etree.XMLSyntaxError:
            raise
        except IOError:
            raise

        if schema_filename:
            try:
                xmlschema = etree.XMLSchema(etree.parse(schema_filename))
            except etree.XMLSyntaxError:
                raise
            except IOError:
                raise
        else:
            xmlschema = getSchemas(doc=doc)

        self.set_progress(100, total=100)

        return xmlschema.validate(doc)

    def undo(self, xml_filename=None, schema_filename=None):
        pass

    def get_event_args(self, xml_filename=None, schema_filename=None):
        return [xml_filename]


class ValidateLogicalPhysicalRepresentation(DBTask):
    event_type = 10262

    """
    Validates the logical and physical representation of objects
    """

    def run(self, ip=None, mets_path=None):
        objpath = ip.ObjectPath

        metsdoc = etree.ElementTree(file=mets_path)

        root = metsdoc.getroot()
        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}

        logical_files = []
        physical_files = []

        for f in metsdoc.xpath('.//mets:file | .//mets:mdRef', namespaces=nsmap):
            if f.tag == "{%s}mdRef" % nsmap['mets']:
                filename = f.get('{%s}href' % nsmap['xlink'])
            else:
                filename = f.find('mets:FLocat', nsmap).get('{%s}href' % nsmap['xlink'])

            filename = os.path.join(objpath, filename)
            logical_files.append(filename)

        for root, dirs, files in os.walk(objpath):
            for f in files:
                filename = os.path.join(root, str(f))

                if filename != mets_path:
                    physical_files.append(filename)

        print "logical: %s" % logical_files
        print "physical: %s" % physical_files

        self.set_progress(100, total=100)
        return logical_files == physical_files

    def undo(self, ip=None, mets_path=None):
        pass

    def get_event_args(self, ip=None, mets_path=None):
        return [mets_path, ip.ObjectPath]


class ValidateIntegrity(DBTask):
    event_type = 10263

    def run(self, filename=None, checksum=None, block_size=65536, algorithm=hashlib.sha256):
        """
        Validates the integrity(checksum) for the given file
        """

        t = ProcessTask(
            name="preingest.tasks.CalculateChecksum",
            params={
                "filename": filename,
                "block_size": block_size,
                "algorithm": algorithm
            },
            information_package=self.taskobj.information_package
        )

        digest = t.run_eagerly()

        self.set_progress(100, total=100)

        return digest == checksum

    def undo(self, filename=None,checksum=None,  block_size=65536, algorithm=hashlib.sha256):
        pass

    def get_event_args(self, filename=None,checksum=None,  block_size=65536, algorithm=hashlib.sha256):
        return [filename, algorithm, checksum]


class CreateTAR(DBTask):
    event_type = 10270

    """
    Creates a TAR file from the specified directory

    Args:
        dirname: The directory to create a TAR from
        tarname: The name of the tar file
    """

    def run(self, dirname=None, tarname=None):
        base_dir = os.path.basename(os.path.normpath(dirname))

        with tarfile.TarFile(tarname, 'w') as new_tar:
            new_tar.add(dirname, base_dir)

        self.set_progress(100, total=100)

    def undo(self, dirname=None, tarname=None):
        pass

    def get_event_args(self, dirname=None, tarname=None):
        return [tarname, dirname]


class CreateZIP(DBTask):
    event_type = 10271

    """
    Creates a ZIP file from the specified directory

    Args:
        dirname: The directory to create a ZIP from
        zipname: The name of the zip file
    """

    def run(self, dirname=None, zipname=None):
        with zipfile.ZipFile(zipname, 'w') as new_zip:
            for root, dirs, files in os.walk(dirname):
                for d in dirs:
                    filepath = os.path.join(root, d)
                    arcname = filepath[len(dirname) + 1:]
                    new_zip.write(filepath, arcname)
                for f in files:
                    filepath = os.path.join(root, f)
                    arcname = filepath[len(dirname) + 1:]
                    new_zip.write(filepath, arcname)

        self.set_progress(100, total=100)

    def undo(self, dirname=None, zipname=None):
        pass

    def get_event_args(self, dirname=None, zipname=None):
        return [zipname, dirname]

class UpdateIPStatus(DBTask):
    event_type = 10280

    def run(self, ip=None, status=None):
        ip.State = status
        ip.save()
        self.set_progress(100, total=100)

    def undo(self, ip=None, status=None):
        pass

    def get_event_args(self, ip=None, status=None):
        return [ip.Label]
