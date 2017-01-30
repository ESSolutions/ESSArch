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
        ('profiles', '0002_auto_20160823_1604'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfilePreservationMetadata',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_preservation_metadata_name', models.CharField(max_length=255)),
                ('profile_preservation_metadata_type', models.CharField(max_length=255)),
                ('profile_preservation_metadata_status', models.CharField(max_length=255)),
                ('profile_preservation_metadata_label', models.CharField(max_length=255)),
                ('profile_preservation_metadata_specification', models.TextField()),
                ('profile_preservation_metadata_data', models.TextField()),
            ],
            options={
                'ordering': ['profile_preservation_metadata_name'],
                'verbose_name': 'Profile Preservation Metadata',
            },
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='archival_description_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='archival_information_package_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='archive_policy',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='authority_information_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='container_format',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='container_format_compression',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='content_type_specification_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='dissemination_information_package_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='information_package_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='ip_event_description_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='mimetypes_definition_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='preservation_description_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='preservation_organization_receiver_email',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='preservation_organization_receiver_url',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submission_information_package_file',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submission_mitigation',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submission_reception_exception_handling',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submission_reception_receipt_confirmation',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submission_reception_validation',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submission_risk',
        ),
        migrations.RemoveField(
            model_name='profiletransferproject',
            name='submit_description_file',
        ),
        migrations.AddField(
            model_name='profileclassification',
            name='profile_classification_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profilecontenttype',
            name='profile_content_type_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profiledataselection',
            name='profile_data_selection_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profileimport',
            name='profile_import_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profilesubmitdescription',
            name='profile_sd_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profiletransferproject',
            name='profile_transfer_project_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profiletransferproject',
            name='profile_transfer_project_specification',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='profileworkflow',
            name='profile_workflow_data',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_aip',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_classification',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_content_type',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_data_selection',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_dip',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_import',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_preservation_metadata',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_sip',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_submit_description',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_transfer_project',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='default_profile_workflow',
            field=models.CharField(default=b'', max_length=255),
        ),
        migrations.AddField(
            model_name='submissionagreement',
            name='profile_preservation_metadata',
            field=models.CharField(default=b'', max_length=255),
        ),
    ]
