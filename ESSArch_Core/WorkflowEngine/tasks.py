from __future__ import absolute_import

import os
import shutil
import sys
import tarfile
import time

from esscore.metadata.metadataGenerator import xmlGenerator
from configuration.models import EventType, Path
from preingest.dbtask import DBTask
from ip.models import EventIP, InformationPackage
from preingest.models import ProcessStep

class Sleepy(DBTask):
    def run(self, foo=None):
        print "run task with id {}".format(self.request.id)
        self.set_progress(0, total=5)
        time.sleep(1)
        self.set_progress(1, total=5)
        time.sleep(1)
        self.set_progress(2, total=5)
        time.sleep(1)
        self.set_progress(3, total=5)
        time.sleep(1)
        self.set_progress(4, total=5)
        time.sleep(1)
        self.set_progress(5, total=5)
        return foo

    def undo(self, foo=None):
        print "undoing task with id {}".format(self.request.id)


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

        self.set_progress(100, total=100)

        return str(ip.id)

    def undo(self, label="", responsible={}):
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

    def run(self, information_package_id=None):
        """
        Creates the IP root directory

        Args:
            information_package_id: The id of the information package the
            directory will be created for

        Returns:
            None
        """

        path = self.create_path(information_package_id)
        os.makedirs(path)

        self.set_progress(100, total=100)
        return information_package_id

    def undo(self, information_package_id=None):
        path = self.create_path(information_package_id)
        shutil.rmtree(path)


class CreateEvent(DBTask):
    def run(self, information_package_id=None, detail=""):
        """
        Creates a new event and saves it to the database

        Args:
            detail: The detail of the event
            information_package_id: The id of the IP connected to the event

        Returns:
            The created event
        """

        ip = InformationPackage.objects.get(
            pk=information_package_id
        )

        self.set_progress(100, total=100)

        event = EventIP.objects.create(
            eventType=EventType.objects.get(
                eventType=10100
            ),
            eventDetail=detail,
            linkingAgentIdentifierValue="System",
            linkingObjectIdentifierValue=ip,
        )

        return event.id

    def undo(self, detail="", information_package_id=None):
        pass


class CreatePhysicalModel(DBTask):

    def run(self, structure={}, root=""):
        """
        Creates the IP physical model based on a logical model.

        Args:
            structure: A dict specifying the logical model.
            root: The root dictionary to be used
        """

        root = str(root)

        for k, v in structure.iteritems():
            k = str(k)
            dirname = os.path.join(root, k)
            os.makedirs(dirname)

            if isinstance(v, dict):
                self.run(v, dirname)

        self.set_progress(1, total=1)

    def undo(self, structure={}, root=""):
        root = str(root)

        if root:
            shutil.rmtree(root)
            return

        for k, v in structure.iteritems():
            k = str(k)
            dirname = os.path.join(root, k)
            shutil.rmtree(dirname)

class GenerateXML(DBTask):
    def run(self, info={}, filesToCreate={}, folderToParse=""):
        archivist = info["ArchivistOrganization"]
        creator = info["CreatorOrganization"]
        producer = info["ProducerOrganization"]
        ipOwner = info["IpOwnerOrganization"]
        editor = info["EditorOrganization"]
        preservation = info["PreservationOrganization"]

        agents = [
            {
                "ROLE": "ARCHIVIST",
                "TYPE": "ORGANIZATION",
                "name": archivist["ArchivistOrganization"],
                "note": archivist["ArchivistOrganizationIdentity"]
            },
            {
                "ROLE": "ARCHIVIST",
                "TYPE": "OTHER",
                "OTHERTYPE": "SOFTWARE",
                "name": archivist["ArchivistOrganizationSoftware"],
                "note": archivist["ArchivistOrganizationSoftwareIdentity"]
            },
            {
                "ROLE": "CREATOR",
                "TYPE": "ORGANIZATION",
                "name": creator["CreatorOrganization"],
                "note": creator["CreatorOrganizationIdentity"]
            },
            {
                "ROLE": "CREATOR",
                "TYPE": "OTHER",
                "OTHERTYPE": "SOFTWARE",
                "name": creator["CreatorOrganizationSoftware"],
                "note": creator["CreatorOrganizationSoftwareIdentity"]
            },
            {
                "ROLE": "PRODUCER",
                "TYPE": "ORGANIZATION",
                "name": producer["ProducerOrganization"]
            },
            {
                "ROLE": "PRODUCER",
                "TYPE": "INDIVIDUAL",
                "name": producer["ProducerIndividual"]
            },
            {
                "ROLE": "PRODUCER",
                "TYPE": "OTHER",
                "OTHERTYPE": "SOFTWARE",
                "name": producer["ProducerOrganizationSoftware"],
                "note": producer["ProducerOrganizationSoftwareIdentity"]
            },
            {
                "ROLE": "IPOWNER",
                "TYPE": "ORGANIZATION",
                "name": ipOwner["IpOwnerOrganization"]
            },
            {
                "ROLE": "IPOWNER",
                "TYPE": "INDIVIDUAL",
                "name": ipOwner["IpOwnerIndividual"],
            },
            {
                "ROLE": "IPOWNER",
                "TYPE": "OTHER",
                "OTHERTYPE": "SOFTWARE",
                "name": ipOwner["IpOwnerOrganizationSoftware"],
                "note": ipOwner["IpOwnerOrganizationSoftwareIdentity"]
            },
            {
                "ROLE": "EDITOR",
                "TYPE": "ORGANIZATION",
                "name": editor["EditorOrganization"]
            },
            {
                "ROLE": "EDITOR",
                "TYPE": "INDIVIDUAL",
                "name": editor["EditorIndividual"]
            },
            {
                "ROLE": "EDITOR",
                "TYPE": "OTHER",
                "OTHERTYPE": "SOFTWARE",
                "name": editor["EditorOrganizationSoftware"],
                "note": editor["EditorOrganizationSoftwareIdentity"]
            },
            {
                "ROLE": "PRESERVATION",
                "TYPE": "ORGANIZATION",
                "name": preservation["PreservationOrganization"]
            },
            {
                "ROLE": "PRESERVATION",
                "TYPE": "INDIVIDUAL",
                "name": preservation["PreservationIndividual"]
            },
            {
                "ROLE": "PRESERVATION",
                "TYPE": "OTHER",
                "OTHERTYPE": "SOFTWARE",
                "name": preservation["PreservationOrganizationSoftware"],
                "note": preservation["PreservationOrganizationSoftwareIdentity"]
            },
        ]

        info = {
            "xmlns:mets": "http://www.loc.gov/METS/",
            "xmlns:ext": "ExtensionMETS",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.loc.gov/METS/ http://xml.ra.se/e-arkiv/METS/CSPackageMETS.xsd ExtensionMETS http://xml.ra.se/e-arkiv/METS/CSPackageExtensionMETS.xsd",
            "xsi:schemaLocationPremis": "http://www.loc.gov/premis/v3 https://www.loc.gov/standards/premis/premis.xsd",
            "PROFILE": "http://xml.ra.se/e-arkiv/METS/CommonSpecificationSwedenPackageProfile.xmll",
            "LABEL": "Test of SIP 1",
            "TYPE": "Personnel",
            "OBJID": "UUID:9bc10faa-3fff-4a8f-bf9a-638841061065",
            "ext:CONTENTTYPESPECIFICATION": "FGS Personal, version 1",
            "CREATEDATE": "2016-06-08T10:44:00+02:00",
            "RECORDSTATUS": "NEW",
            "ext:OAISTYPE": "SIP",
            "agentName": "name",
            "agentNote": "note",
            "REFERENCECODE": "SE/RA/123456/24/F",
            "SUBMISSIONAGREEMENT": "RA 13-2011/5329, 2012-04-12",
            "MetsIdentifier": "sip.xml",
            "filename":"sip.txt",
            "SMLabel":"Profilestructmap",
            "amdLink":"IDce745fec-cfdd-4d14-bece-d49e867a2487",
            "digiprovLink":"IDa32a20cb-5ff8-4d36-8202-f96519154de2",
            "LOCTYPE":"URL",
            "MDTYPE":"PREMIS",
            "xlink:href":"file:///metadata/premis.xml",
            "xlink:type":"simple",
            "ID":"ID31e51159-9280-44d1-b26c-014077f8eeb5",
            "agents": agents
        }

        xmlGenerator.createXML(info, filesToCreate, folderToParse)
        self.set_progress(1, total=1)

    def undo(self, info={}, filesToCreate={}, folderToParse=""):
        for f, template in filesToCreate.iteritems():
            try:
                os.remove(f)
            except:
                pass

class UploadFile(DBTask):
    def run(self, src_file=None, dst_file=None):
        self.set_progress(1, total=1)

    def undo(self, src_file=None, dst_file=None):
        pass

class CreateIPEventsFile(DBTask):
    def run(self, events=[]):
        for event in events:
            print "Adding event {}".format(event)

        self.set_progress(1, total=1)

    def undo(self):
        pass

class AddPremisToMetsAmdSec(DBTask):
    def run(self, data={}):
        self.set_progress(1, total=1)

    def undo(self, data={}):
        pass

class ValidateMetadata(DBTask):
    def run(self, metadata_file=None, schema_file=None):
        self.set_progress(1, total=1)

    def undo(self, metadata_file=None, schema_file=None):
        pass

class ValidateLogicalPhysical(DBTask):
    def run(self, structure={}):
        self.set_progress(1, total=1)

    def undo(self, structure={}):
        pass

class CreateTAR(DBTask):
    def run(self, archive_object):
        tarpath = archive_object + ".tar"

        with tarfile.open(tarpath, "w") as tar:
            tar.add(archive_object)

        self.set_progress(1, total=1)

    def undo(self, archive_object):
        try:
            os.remove(archive_object + ".tar")
        except:
            pass

class First(DBTask):
    def run(self, foo=None):
        print "run task with name {} and id {}".format(self.__name__, self.request.id)
        self.set_progress(1, total=1)
        print "completed task with name {} and id {}".format(self.__name__, self.request.id)
        return foo

    def undo(self, foo=None):
        print "undo task with name {} and id {}".format(self.__name__, self.request.id)
        self.set_progress(1, total=1)

class Second(DBTask):
    def run(self, foo=None):
        print "run task with name {} and id {}".format(self.__name__, self.request.id)
        self.set_progress(1, total=2)
        self.set_progress(2, total=2)
        print "completed task with name {} and id {}".format(self.__name__, self.request.id)
        return foo

    def undo(self, foo=None):
        print "undo task with name {} and id {}".format(self.__name__, self.request.id)
        self.set_progress(1, total=2)
        self.set_progress(2, total=2)

class Third(DBTask):
    def run(self, foo=None):
        print "run task with name {} and id {}".format(self.__name__, self.request.id)
        self.set_progress(1, total=1)
        self.set_progress(2, total=2)
        self.set_progress(3, total=3)
        print "completed task with name {} and id {}".format(self.__name__, self.request.id)
        return foo

    def undo(self, foo=None):
        print "undo task with name {} and id {}".format(self.__name__, self.request.id)
        self.set_progress(1, total=1)
        self.set_progress(2, total=2)
        self.set_progress(3, total=3)
