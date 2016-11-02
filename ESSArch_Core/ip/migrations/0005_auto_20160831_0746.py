# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0004_auto_20160831_0745'),
    ]

    operations = [
        migrations.RenameField(
            model_name='informationpackage',
            old_name='SA',
            new_name='SubmissionAgreement',
        ),
    ]
