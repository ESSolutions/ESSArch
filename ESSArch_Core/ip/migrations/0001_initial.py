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
        ('guardian', '0001_initial')
    ]

    operations = [
        migrations.CreateModel(
            name='EventIP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('eventType', models.CharField(max_length=255)),
                ('eventDateTime', models.CharField(max_length=255)),
                ('eventDetail', models.CharField(max_length=255)),
                ('eventApplication', models.CharField(max_length=255)),
                ('eventVersion', models.CharField(max_length=255)),
                ('eventOutcome', models.CharField(max_length=255)),
                ('eventOutcomeDetailNote', models.CharField(max_length=1024)),
                ('linkingAgentIdentifierValue', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['eventType'],
                'verbose_name': 'Events related to IP',
            },
        ),
        migrations.CreateModel(
            name='InformationPackage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('Producer', models.CharField(max_length=255)),
                ('Label', models.CharField(max_length=255)),
                ('Content', models.CharField(max_length=255)),
                ('Responsible', models.CharField(max_length=255)),
                ('CreateDate', models.CharField(max_length=255, verbose_name='create date')),
                ('State', models.CharField(max_length=255, verbose_name='state')),
                ('Status', models.CharField(max_length=255)),
                ('ObjectSize', models.CharField(max_length=255)),
                ('ObjectNumItems', models.CharField(max_length=255)),
                ('ObjectPath', models.CharField(max_length=255)),
                ('Startdate', models.CharField(max_length=255, verbose_name='start date')),
                ('Enddate', models.CharField(max_length=255, verbose_name='end date')),
                ('OAIStype', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['id'],
                'verbose_name': 'Information Package',
            },
        ),
        migrations.AddField(
            model_name='eventip',
            name='linkingObjectIdentifierValue',
            field=models.ForeignKey(on_delete=models.CASCADE, related_name='events', to='ip.InformationPackage'),
        ),
    ]
