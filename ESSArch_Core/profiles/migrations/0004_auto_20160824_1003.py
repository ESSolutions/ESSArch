"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_auto_20160823_2313'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileAIPRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profileaip', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileAIP')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileAIP',
            },
        ),
        migrations.CreateModel(
            name='ProfileClassificationRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profileclassification', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileClassification')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileClassification',
            },
        ),
        migrations.CreateModel(
            name='ProfileContentTypeRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profilecontenttype', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileContentType')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileContentType',
            },
        ),
        migrations.CreateModel(
            name='ProfileDataSelectionRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profiledataselection', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileDataSelection')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileDataSelection',
            },
        ),
        migrations.CreateModel(
            name='ProfileDIPRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profiledip', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileDIP')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileDIP',
            },
        ),
        migrations.CreateModel(
            name='ProfileImportRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profileimport', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileImport')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileImport',
            },
        ),
        migrations.CreateModel(
            name='ProfilePreservationMetadataRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profilepreservationmetadata', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfilePreservationMetadata')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfilePreservationMetadata',
            },
        ),
        migrations.CreateModel(
            name='ProfileSIPRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profilesip', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileSIP')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileSIP',
            },
        ),
        migrations.CreateModel(
            name='ProfileSubmitDescriptionRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profilesubmitdescription', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileSubmitDescription')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileSubmitDescription',
            },
        ),
        migrations.CreateModel(
            name='ProfileTransferProjectRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profiletransferproject', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileTransferProject')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileTransferProject',
            },
        ),
        migrations.CreateModel(
            name='ProfileWorkflowRel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('status', models.IntegerField(default=0, verbose_name='Profile status', choices=[(0, 'Disabled'), (1, 'Enabled'), (2, 'Default')])),
                ('profileworkflow', models.ForeignKey(on_delete=models.CASCADE, to='profiles.ProfileWorkflow')),
            ],
            options={
                'ordering': ['status'],
                'verbose_name': 'ProfileWorkflow',
            },
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_aip',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_classification',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_content_type',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_data_selection',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_dip',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_import',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_preservation_metadata',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_sip',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_submit_description',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_transfer_project',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='default_profile_workflow',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_aip',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_classification',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_content_type',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_data_selection',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_dip',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_import',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_preservation_metadata',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_sip',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_submit_description',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_transfer_project',
        ),
        migrations.RemoveField(
            model_name='submissionagreement',
            name='profile_workflow',
        ),
        migrations.AddField(
            model_name='profileworkflowrel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profiletransferprojectrel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profilesubmitdescriptionrel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profilesiprel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profilepreservationmetadatarel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profileimportrel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profilediprel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profiledataselectionrel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profilecontenttyperel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profileclassificationrel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
        migrations.AddField(
            model_name='profileaiprel',
            name='submissionagreement',
            field=models.ForeignKey(on_delete=models.CASCADE, to='profiles.SubmissionAgreement'),
        ),
    ]
