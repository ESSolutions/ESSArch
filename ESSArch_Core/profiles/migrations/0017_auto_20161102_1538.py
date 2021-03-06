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
# Generated by Django 1.10 on 2016-11-02 14:38
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0016_auto_20161011_0914'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='cm_change_authority',
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='cm_change_description',
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='cm_release_date',
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='cm_sections_affected',
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='cm_version',
            field=models.CharField(blank=True, max_length=255),
            preserve_default=False,
        ),
    ]
