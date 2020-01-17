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
            name='EventType',
            fields=[
                ('eventType', models.IntegerField(default=0, primary_key=True, serialize=False)),
                ('eventDetail', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['eventType'],
                'verbose_name': 'Event Type',
            },
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('entity', models.CharField(unique=True, max_length=60, verbose_name='entity')),
                ('value', models.CharField(max_length=70, verbose_name='value')),
            ],
            options={
                'ordering': ['entity'],
                'verbose_name': 'parameter',
                'verbose_name_plural': 'parameters',
            },
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('entity', models.CharField(unique=True, max_length=60, verbose_name='entity')),
                ('value', models.CharField(max_length=70, verbose_name='value')),
            ],
            options={
                'ordering': ['entity'],
                'verbose_name': 'path',
                'verbose_name_plural': 'paths',
            },
        ),
        migrations.CreateModel(
            name='Schema',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('entity', models.CharField(unique=True, max_length=60)),
                ('value', models.CharField(max_length=70)),
            ],
            options={
                'ordering': ['entity'],
                'verbose_name': 'XML Schema',
            },
        ),
    ]
