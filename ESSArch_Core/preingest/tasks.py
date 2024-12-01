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
import shutil

from django.contrib.auth import get_user_model
from django.db import transaction

# noinspection PyUnresolvedReferences
from ESSArch_Core import tasks  # noqa
from ESSArch_Core.config.celery import app
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import Agent, InformationPackage

User = get_user_model()


@app.task(bind=True, event_type=20100)
@transaction.atomic
def ReceiveIP(self):
    ip = InformationPackage.objects.get(pk=self.ip)
    sa = ip.submission_agreement
    preingest_path = Path.objects.get(entity="preingest").value
    dst_dir = os.path.join(preingest_path, ip.object_identifier_value)
    shutil.copytree(ip.object_path, dst_dir)

    if sa.archivist_organization:
        existing_agents_with_notes = Agent.objects.all().with_notes([])
        ao_agent, _ = Agent.objects.get_or_create(
            role='ARCHIVIST', type='ORGANIZATION',
            name=sa.archivist_organization, pk__in=existing_agents_with_notes
        )
        ip.agents.add(ao_agent)

    submit_description_data = ip.get_profile_data('submit_description')
    ip.label = ip.object_identifier_value
    ip.entry_date = ip.create_date
    ip.object_path = dst_dir
    ip.start_date = submit_description_data.get('start_date')
    ip.end_date = submit_description_data.get('end_date')
    ip.save()

    self.create_success_event("Received IP ({})".format(ip.object_identifier_value))
