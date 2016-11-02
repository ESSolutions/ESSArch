# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0008_auto_20160830_1023'),
        ('ip', '0003_auto_20160823_2313'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='informationpackage',
            name='SubmissionAgreement',
        ),
        migrations.AddField(
            model_name='informationpackage',
            name='SA',
            field=models.ForeignKey(default=None, to='profiles.SubmissionAgreement', null=True),
        ),
    ]
