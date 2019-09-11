"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Archive (ETA)
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

import os

import requests
from django.conf import settings
from django.contrib.auth import get_user_model

# noinspection PyUnresolvedReferences
from ESSArch_Core import tasks  # noqa
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.storage.copy import copy_file
from ESSArch_Core.WorkflowEngine.dbtask import DBTask

User = get_user_model()


class TransferSIP(DBTask):
    event_type = 20600

    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        src = ip.object_path
        srcdir, srcfile = os.path.split(src)
        epp = Path.objects.get(entity="path_gate_reception").value

        try:
            remote = ip.get_profile_data('transfer_project').get(
                'preservation_organization_receiver_url_epp'
            )
        except AttributeError:
            remote = None

        session = None

        if remote:
            try:
                dst, remote_user, remote_pass = remote.split(',')

                session = requests.Session()
                session.verify = settings.REQUESTS_VERIFY
                session.auth = (remote_user, remote_pass)
            except ValueError:
                remote = None
        else:
            dst = os.path.join(epp, srcfile)

        block_size = 8 * 1000000  # 8MB

        copy_file(src, dst, requests_session=session, block_size=block_size)

        self.set_progress(50, total=100)

        objid = ip.object_identifier_value
        src = ip.get_events_file_path()
        if os.path.isfile(src):
            if not remote:
                dst = os.path.join(epp, "%s_ipevents.xml" % objid)
            copy_file(src, dst, requests_session=session, block_size=block_size)

        self.set_progress(75, total=100)

        src = os.path.join(srcdir, "%s.xml" % objid)
        if not remote:
            dst = os.path.join(epp, "%s.xml" % objid)
        copy_file(src, dst, requests_session=session, block_size=block_size)

        self.set_progress(100, total=100)

        return dst

    def undo(self):
        objectpath = InformationPackage.objects.values_list('object_path', flat=True).get(pk=self.ip)

        ipdir, ipfile = os.path.split(objectpath)
        gate_reception = Path.objects.get(entity="path_gate_reception").value

        objid = InformationPackage.objects.values_list(
            'object_identifier_value', flat=True
        ).get(pk=self.ip)

        os.remove(os.path.join(gate_reception, ipfile))
        os.remove(os.path.join(gate_reception, "%s.xml" % objid))

    def event_outcome_success(self, result, *args, **kwargs):
        return "Transferred IP"
