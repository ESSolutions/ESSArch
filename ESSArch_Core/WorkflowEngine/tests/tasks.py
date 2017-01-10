from __future__ import absolute_import

from ESSArch_Core.WorkflowEngine.dbtask import DBTask

import os


class First(DBTask):
    def run(self, foo=None):
        self.set_progress(1, total=1)
        return foo

    def undo(self, foo=None):
        pass


class Second(DBTask):
    def run(self, foo=None):
        self.set_progress(1, total=2)
        return foo

    def undo(self, foo=None):
        pass


class Third(DBTask):
    def run(self, foo=None):
        self.set_progress(1, total=1)
        return foo

    def undo(self, foo=None):
        pass


class Add(DBTask):
    def run(self, x=None, y=None):
        self.set_progress(1, total=1)
        return x+y

    def undo(self, x=None, y=None):
        pass


class Fail(DBTask):
    def run(self):
        raise Exception

    def undo(self):
        pass


class FailIfFileNotExists(DBTask):
    def run(self, filename=None):
        assert os.path.isfile(filename)
        self.set_progress(1, total=1)
        return filename

    def undo(self, filename=None):
        pass
