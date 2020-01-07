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

# -*- coding: utf-8 -*-
from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SubmissionAgreement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('type', models.CharField(max_length=255)),
                ('status', models.CharField(max_length=255)),
                ('label', models.CharField(max_length=255)),
                ('cm_version', models.CharField(blank=True, max_length=255)),
                ('cm_release_date', models.CharField(blank=True, max_length=255)),
                ('cm_change_authority', models.CharField(blank=True, max_length=255)),
                ('cm_change_description', models.CharField(blank=True, max_length=255)),
                ('cm_sections_affected', models.CharField(blank=True, max_length=255)),
                ('producer_organization', models.CharField(blank=True, max_length=255)),
                ('producer_main_name', models.CharField(blank=True, max_length=255)),
                ('producer_main_address', models.CharField(blank=True, max_length=255)),
                ('producer_main_phone', models.CharField(blank=True, max_length=255)),
                ('producer_main_email', models.CharField(blank=True, max_length=255)),
                ('producer_main_additional', models.CharField(blank=True, max_length=255)),
                ('producer_individual_name', models.CharField(blank=True, max_length=255)),
                ('producer_individual_role', models.CharField(blank=True, max_length=255)),
                ('producer_individual_phone', models.CharField(blank=True, max_length=255)),
                ('producer_individual_email', models.CharField(blank=True, max_length=255)),
                ('producer_individual_additional', models.CharField(blank=True, max_length=255)),
                ('archivist_organization', models.CharField(blank=True, max_length=255)),
                ('archivist_main_name', models.CharField(blank=True, max_length=255)),
                ('archivist_main_address', models.CharField(blank=True, max_length=255)),
                ('archivist_main_phone', models.CharField(blank=True, max_length=255)),
                ('archivist_main_email', models.CharField(blank=True, max_length=255)),
                ('archivist_main_additional', models.CharField(blank=True, max_length=255)),
                ('archivist_individual_name', models.CharField(blank=True, max_length=255)),
                ('archivist_individual_role', models.CharField(blank=True, max_length=255)),
                ('archivist_individual_phone', models.CharField(blank=True, max_length=255)),
                ('archivist_individual_email', models.CharField(blank=True, max_length=255)),
                ('archivist_individual_additional', models.CharField(blank=True, max_length=255)),
                ('designated_community_description', models.CharField(blank=True, max_length=255)),
                ('designated_community_individual_name', models.CharField(blank=True, max_length=255)),
                ('designated_community_individual_role', models.CharField(blank=True, max_length=255)),
                ('designated_community_individual_phone', models.CharField(blank=True, max_length=255)),
                ('designated_community_individual_email', models.CharField(blank=True, max_length=255)),
                ('designated_community_individual_additional', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Submission Agreement',
            },
        ),
    ]
