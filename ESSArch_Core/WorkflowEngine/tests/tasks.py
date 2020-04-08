"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import os

from ESSArch_Core.config.celery import app
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.dbtask import DBTask


class First(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.First'

    def run(self, foo=None):
        return foo


class Second(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.Second'

    def run(self, foo=None):
        self.set_progress(1, total=2)
        return foo


class Third(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.Third'

    def run(self, foo=None):
        return foo


class Add(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.Add'

    def run(self, x, y):
        return x + y


class Fail(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.Fail'

    def run(self):
        raise ValueError('An error occurred!')


class FailDoesNotExist(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.FailDoesNotExist'

    def run(self):
        raise InformationPackage.DoesNotExist


class FailIfFileNotExists(DBTask):
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.FailIfFileNotExists'

    def run(self, filename=None):
        assert os.path.isfile(filename)
        return filename


class WithEvent(DBTask):
    event_type = 1
    name = 'ESSArch_Core.WorkflowEngine.tests.tasks.WithEvent'

    def run(self, bar, foo=None):
        return foo

    def event_outcome_success(self, result, bar, foo=None):
        return "Task completed successfully with bar=%s and foo=%s" % (bar, foo)


app.tasks.register(First())
app.tasks.register(Second())
app.tasks.register(Third())
app.tasks.register(Add())
app.tasks.register(Fail())
app.tasks.register(FailDoesNotExist())
app.tasks.register(FailIfFileNotExists())
app.tasks.register(WithEvent())
