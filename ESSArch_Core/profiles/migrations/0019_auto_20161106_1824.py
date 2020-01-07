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
# Generated by Django 1.10 on 2016-11-06 17:24
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ip', '0014_auto_20160913_1557'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('profiles', '0018_auto_20161104_1624'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileSALock',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('Unlockable', models.BooleanField(default=False)),
                ('LockedBy', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.Profile')),
                ('submission_agreement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.SubmissionAgreement')),
            ],
        ),
        migrations.CreateModel(
            name='SAIPLock',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('Unlockable', models.BooleanField(default=False)),
                ('LockedBy', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('information_package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ip.InformationPackage')),
                ('submission_agreement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.SubmissionAgreement')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='profilelock',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='profilelock',
            name='LockedBy',
        ),
        migrations.RemoveField(
            model_name='profilelock',
            name='information_package',
        ),
        migrations.RemoveField(
            model_name='profilelock',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='profilelock',
            name='submission_agreement',
        ),
        migrations.DeleteModel(
            name='ProfileLock',
        ),
        migrations.AlterUniqueTogether(
            name='saiplock',
            unique_together=set([('submission_agreement', 'information_package')]),
        ),
        migrations.AlterUniqueTogether(
            name='profilesalock',
            unique_together=set([('profile', 'submission_agreement')]),
        ),
    ]
