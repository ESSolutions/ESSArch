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


@app.task(bind=True)
def First(self, foo=None):
    return foo


@app.task(bind=True)
def Second(self, foo=None):
    self.set_progress(1, total=2)
    return foo


@app.task(bind=True)
def Third(self, foo=None):
    return foo


@app.task(bind=True)
def Add(self, x, y):
    return x + y


@app.task(bind=True)
def Fail(self):
    raise ValueError('An error occurred!')


@app.task(bind=True)
def FailDoesNotExist(self):
    raise InformationPackage.DoesNotExist


@app.task(bind=True)
def FailIfFileNotExists(self, filename=None):
    assert os.path.isfile(filename)
    return filename


@app.task(bind=True)
def WithEvent(self, bar, foo=None):
    self.event_type = 1

    msg = "Task completed successfully with bar=%s and foo=%s" % (bar, foo)
    self.create_success_event(msg)

    return foo
