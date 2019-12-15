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


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0002_auto_20160823_1220'),
    ]

    operations = [
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivalInstitution',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivalLocation',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivalType',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivistOrganization',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='SubmissionAgreement',
            field=models.CharField(default='', max_length=255),
        ),
    ]
