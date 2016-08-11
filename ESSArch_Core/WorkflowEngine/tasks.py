from __future__ import absolute_import

import os
import shutil
import sys
import time

from preingest.dbtask import DBTask

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
    def run(self, data={}):
        sys.path.append("../ESSArch_TP/esscore/metadata/metadataGenerator")
        import xmlGenerator
        xmlGenerator.createXML(data)
        self.set_progress(1, total=1)

    def undo(self, data={}):
        key = "filesToCreate"
        if key in data:
            for f, _ in data[key].iteritems():
                os.remove(f)

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
    def run(self):
        self.set_progress(1, total=1)

    def undo(self):
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
