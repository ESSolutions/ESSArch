from __future__ import absolute_import

import os
import shutil

from configuration.models import EventType, Path
from preingest.dbtask import DBTask
from ip.models import EventIP, InformationPackage
from preingest.models import ProcessStep

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

        self.set_progress(100, total=100)
        return information_package

    def undo(self, information_package=None):
        path = self.create_path(information_package.pk)
        shutil.rmtree(path)


class CreateEvent(DBTask):
    def run(self, information_package=None, detail=""):
        """
        Creates a new event and saves it to the database

        Args:
            detail: The detail of the event
            information_package_id: The id of the IP connected to the event

        Returns:
            The created event
        """


        event = EventIP.objects.create(
            eventType=EventType.objects.get(
                eventType=10100
            ),
            eventDetail=detail,
            linkingAgentIdentifierValue="System",
            linkingObjectIdentifierValue=information_package,
        )

        self.set_progress(100, total=100)
        return event.id

    def undo(self, information_package=None, detail=""):
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
