from __future__ import absolute_import

import hashlib, os, shutil, tarfile, urllib, zipfile

from django.conf import settings

from demo.xmlGenerator import createXML, appendXML

from lxml import etree

from configuration.models import Path
from preingest.dbtask import DBTask
from ip.models import InformationPackage
from preingest.models import ProcessStep
from preingest.util import create_event, getSchemas

class PrepareIP(DBTask):
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

        if step is not None:
            s = ProcessStep.objects.get(pk=step)
            ip.steps.add(s)

        create_event(10100, "Preparing IP", "System", ip)

        self.set_progress(100, total=100)

        return ip

    def undo(self, label="", responsible={}, step=None):
        pass


class CreateIPRootDir(DBTask):
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

        path = self.create_path(str(information_package.pk))
        os.makedirs(path)

        create_event(
            10100, "Creating IP root directory", "System", information_package
        )

        self.set_progress(100, total=100)
        return information_package

    def undo(self, information_package=None):
        path = self.create_path(information_package.pk)
        shutil.rmtree(path)


class CreatePhysicalModel(DBTask):

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

        create_event(
            10200,"Calculating checksum for %s" % filename, "System",
            self.taskobj.information_package
        )

        self.set_progress(100, total=100)
        return hash_val.hexdigest()

    def undo(self, filename=None, block_size=65536, algorithm=hashlib.sha256):
        pass


class GenerateXML(DBTask):
    """
    Generates the XML using the specified data and folder, and adds the XML to
    the specified files
    """

    def run(self, info={}, filesToCreate={}, folderToParse=None):
        create_event(
            10200,
            "Generating XML files: %s" % ", ".join(filesToCreate.keys()),
            "System", self.taskobj.information_package
        )
        createXML(info, filesToCreate, folderToParse)

        self.set_progress(100, total=100)

    def undo(self, info={}, filesToCreate={}, folderToParse=None):
        for f, template in filesToCreate.iteritems():
            os.remove(f)

class AppendEvents(DBTask):
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

        create_event(
            10200, "Appending events to %s" % (filename), "System",
            self.taskobj.information_package
        )
        self.set_progress(100, total=100)

    def undo(self, filename="", events={}):
        pass

class CopySchemas(DBTask):
    """
    Copies the schemas to a specified (?) location
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

    def run(self, schemas={}, root=None, structure=None):
        for schema in schemas:
            src = schema['location']
            fname = os.path.basename(src.rstrip("/"))
            dst = os.path.join(
                root,
                self.findDestination(schema['preservation_location'], structure),
                fname
            )
            urllib.urlretrieve(src, dst)
            create_event(
                10200,
                "Download from %s to %s" % (src, dst),
                "System", self.taskobj.information_package
            )

        self.set_progress(100, total=100)

    def undo(self, schemas={}, root=None, structure=None):
        pass

class ValidateFileFormat(DBTask):
    """
    Validates the format (PREFORMA, jhove, droid, etc.) of the given file
    """

    def run(self, filename=None, fileformat=None):
        create_event(
            10200,
            "Validate file format for %s against %s" % (filename, fileformat),
            "System", self.taskobj.information_package
        )
        self.set_progress(100, total=100)

    def undo(self, filename=None, fileformat=None):
        pass


class ValidateXMLFile(DBTask):
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

        create_event(
            10200, "Validate %s" % (xml_filename,),
            "System", self.taskobj.information_package
        )
        self.set_progress(100, total=100)

        return xmlschema.validate(doc)

    def undo(self, xml_filename=None, schema_filename=None):
        pass


class ValidateLogicalPhysicalRepresentation(DBTask):
    """
    Validates the logical and physical representation of objects
    """

    def run(self, logical=None, physical=None):
        create_event(
            10200, "Validate %s against %s" % (logical, physical), "System",
            self.taskobj.information_package
        )
        self.set_progress(100, total=100)

    def undo(self, logical=None, physical=None):
        pass


class ValidateIntegrity(DBTask):
    def run(self, filename=None, checksum=None, block_size=65536, algorithm=hashlib.sha256):
        """
        Validates the integrity(checksum) for the given file
        """

        create_event(
            10200,
            "Validating checksum for %s using %s against %s" % (filename, algorithm, checksum),
            "System", self.taskobj.information_package
        )

        self.set_progress(100, total=100)

    def undo(self, filename=None,checksum=None,  block_size=65536, algorithm=hashlib.sha256):
        pass


class CreateTAR(DBTask):
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

        create_event(
            10200, "Create %s.tar from %s" % (tarname, dirname), "System",
            self.taskobj.information_package
        )
        self.set_progress(100, total=100)

    def undo(self, dirname=None, tarname=None):
        pass


class CreateZIP(DBTask):
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

        create_event(
            10200, "Create %s.zip from %s" % (zipname, dirname), "System",
            self.taskobj.information_package
        )

        self.set_progress(100, total=100)

    def undo(self, dirname=None, zipname=None):
        pass

class UpdateIPStatus(DBTask):

    def run(self, ip=None, status=None):
        ip.State = status
        ip.save()
        self.set_progress(100, total=100)

    def undo(self, ip=None, status=None):
        pass
