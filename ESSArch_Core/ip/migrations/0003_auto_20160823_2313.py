# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0002_auto_20160823_1220'),
    ]

    operations = [
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivalInstitution',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivalLocation',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivalType',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='ArchivistOrganization',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='SubmissionAgreement',
            field=models.CharField(default=b'', max_length=255),
        ),
    ]
