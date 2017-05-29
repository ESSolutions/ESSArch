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

from __future__ import absolute_import

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.dbtask import DBTask

import os


class First(DBTask):
    def run(self, foo=None):
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
        return foo

    def undo(self, foo=None):
        pass


class Add(DBTask):
    def run(self, x, y):
        return x+y

    def undo(self, x, y):
        return x-y


class Fail(DBTask):
    def run(self):
        raise Exception

    def undo(self):
        pass


class FailDoesNotExist(DBTask):
    def run(self):
        raise InformationPackage.DoesNotExist

    def undo(self):
        pass


class FailIfFileNotExists(DBTask):
    def run(self, filename=None):
        assert os.path.isfile(filename)
        return filename

    def undo(self, filename=None):
        pass


class WithEvent(DBTask):
    event_type = 1

    def run(self, bar, foo=None):
        return foo

    def undo(self, bar, foo=None):
        pass

    def event_outcome_success(self, bar, foo=None):
        return "Task completed successfully with bar=%s and foo=%s" % (bar, foo)
