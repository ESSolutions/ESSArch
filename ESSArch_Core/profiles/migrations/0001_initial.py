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
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileAIP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_aip_name', models.CharField(max_length=255)),
                ('profile_aip_type', models.CharField(max_length=255)),
                ('profile_aip_status', models.CharField(max_length=255)),
                ('profile_aip_label', models.CharField(max_length=255)),
                ('aip_representation_info', models.CharField(max_length=255)),
                ('aip_preservation_descriptive_info', models.CharField(max_length=255)),
                ('aip_supplemental', models.CharField(max_length=255)),
                ('aip_access_constraints', models.CharField(max_length=255)),
                ('aip_datamodel_reference', models.CharField(max_length=255)),
                ('aip_additional', models.CharField(max_length=255)),
                ('aip_submission_method', models.CharField(max_length=255)),
                ('aip_submission_schedule', models.CharField(max_length=255)),
                ('aip_submission_data_inventory', models.CharField(max_length=255)),
                ('aip_structure', models.TextField()),
                ('aip_specification', models.TextField()),
                ('aip_specification_data', models.TextField()),
            ],
            options={
                'ordering': ['profile_aip_name'],
                'verbose_name': 'Profile AIP',
            },
        ),
        migrations.CreateModel(
            name='ProfileClassification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_classification_name', models.CharField(max_length=255)),
                ('profile_classification_type', models.CharField(max_length=255)),
                ('profile_classification_status', models.CharField(max_length=255)),
                ('profile_classification_label', models.CharField(max_length=255)),
                ('profile_classification_specification', models.TextField()),
            ],
            options={
                'ordering': ['profile_classification_name'],
                'verbose_name': 'Profile Classification',
            },
        ),
        migrations.CreateModel(
            name='ProfileContentType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_content_type_name', models.CharField(max_length=255)),
                ('profile_content_type_type', models.CharField(max_length=255)),
                ('profile_content_type_status', models.CharField(max_length=255)),
                ('profile_content_type_label', models.CharField(max_length=255)),
                ('profile_content_type_specification', models.TextField()),
            ],
            options={
                'ordering': ['profile_content_type_name'],
                'verbose_name': 'Profile Content Type',
            },
        ),
        migrations.CreateModel(
            name='ProfileDataSelection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_data_selection_name', models.CharField(max_length=255)),
                ('profile_data_selection_type', models.CharField(max_length=255)),
                ('profile_data_selection_status', models.CharField(max_length=255)),
                ('profile_data_selection_label', models.CharField(max_length=255)),
                ('profile_data_selection_specification', models.TextField()),
            ],
            options={
                'ordering': ['profile_data_selection_name'],
                'verbose_name': 'Profile Data Selection',
            },
        ),
        migrations.CreateModel(
            name='ProfileDIP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_dip_name', models.CharField(max_length=255)),
                ('profile_dip_type', models.CharField(max_length=255)),
                ('profile_dip_status', models.CharField(max_length=255)),
                ('profile_dip_label', models.CharField(max_length=255)),
                ('dip_representation_info', models.CharField(max_length=255)),
                ('dip_preservation_descriptive_info', models.CharField(max_length=255)),
                ('dip_supplemental', models.CharField(max_length=255)),
                ('dip_access_constraints', models.CharField(max_length=255)),
                ('dip_datamodel_reference', models.CharField(max_length=255)),
                ('dip_additional', models.CharField(max_length=255)),
                ('dip_submission_method', models.CharField(max_length=255)),
                ('dip_submission_schedule', models.CharField(max_length=255)),
                ('dip_submission_data_inventory', models.CharField(max_length=255)),
                ('dip_structure', models.TextField()),
                ('dip_specification', models.TextField()),
                ('dip_specification_data', models.TextField()),
            ],
            options={
                'ordering': ['profile_dip_name'],
                'verbose_name': 'Profile DIP',
            },
        ),
        migrations.CreateModel(
            name='ProfileImport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_import_name', models.CharField(max_length=255)),
                ('profile_import_type', models.CharField(max_length=255)),
                ('profile_import_status', models.CharField(max_length=255)),
                ('profile_import_label', models.CharField(max_length=255)),
                ('profile_import_specification', models.TextField()),
            ],
            options={
                'ordering': ['profile_import_name'],
                'verbose_name': 'Profile Import',
            },
        ),
        migrations.CreateModel(
            name='ProfileSIP',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_sip_name', models.CharField(max_length=255)),
                ('profile_sip_type', models.CharField(max_length=255)),
                ('profile_sip_status', models.CharField(max_length=255)),
                ('profile_sip_label', models.CharField(max_length=255)),
                ('sip_representation_info', models.CharField(max_length=255)),
                ('sip_preservation_descriptive_info', models.CharField(max_length=255)),
                ('sip_supplemental', models.CharField(max_length=255)),
                ('sip_access_constraints', models.CharField(max_length=255)),
                ('sip_datamodel_reference', models.CharField(max_length=255)),
                ('sip_additional', models.CharField(max_length=255)),
                ('sip_submission_method', models.CharField(max_length=255)),
                ('sip_submission_schedule', models.CharField(max_length=255)),
                ('sip_submission_data_inventory', models.CharField(max_length=255)),
                ('sip_structure', models.TextField()),
                ('sip_specification', models.TextField()),
                ('sip_specification_data', models.TextField()),
            ],
            options={
                'ordering': ['profile_sip_name'],
                'verbose_name': 'Profile SIP',
            },
        ),
        migrations.CreateModel(
            name='ProfileSubmitDescription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_sd_name', models.CharField(max_length=255)),
                ('profile_sd_type', models.CharField(max_length=255)),
                ('profile_sd_status', models.CharField(max_length=255)),
                ('profile_sd_label', models.CharField(max_length=255)),
                ('profile_sd_specification', models.TextField()),
            ],
            options={
                'ordering': ['profile_sd_name'],
                'verbose_name': 'Profile Submit Description',
            },
        ),
        migrations.CreateModel(
            name='ProfileTransferProject',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_transfer_project_name', models.CharField(max_length=255)),
                ('profile_transfer_project_type', models.CharField(max_length=255)),
                ('profile_transfer_project_status', models.CharField(max_length=255)),
                ('profile_transfer_project_label', models.CharField(max_length=255)),
                ('archive_policy', models.CharField(max_length=255)),
                ('container_format', models.CharField(max_length=255)),
                ('container_format_compression', models.CharField(max_length=255)),
                ('submission_reception_validation', models.CharField(max_length=255)),
                ('submission_reception_exception_handling', models.CharField(max_length=255)),
                ('submission_reception_receipt_confirmation', models.CharField(max_length=255)),
                ('submission_risk', models.CharField(max_length=255)),
                ('submission_mitigation', models.CharField(max_length=255)),
                ('information_package_file', models.CharField(max_length=255)),
                ('submission_information_package_file', models.CharField(max_length=255)),
                ('archival_information_package_file', models.CharField(max_length=255)),
                ('dissemination_information_package_file', models.CharField(max_length=255)),
                ('submit_description_file', models.CharField(max_length=255)),
                ('content_type_specification_file', models.CharField(max_length=255)),
                ('archival_description_file', models.CharField(max_length=255)),
                ('authority_information_file', models.CharField(max_length=255)),
                ('preservation_description_file', models.CharField(max_length=255)),
                ('ip_event_description_file', models.CharField(max_length=255)),
                ('mimetypes_definition_file', models.CharField(max_length=255)),
                ('preservation_organization_receiver_email', models.CharField(max_length=255)),
                ('preservation_organization_receiver_url', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['profile_transfer_project_name'],
                'verbose_name': 'Profile Transfer Project',
            },
        ),
        migrations.CreateModel(
            name='ProfileWorkflow',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('profile_workflow_name', models.CharField(max_length=255)),
                ('profile_workflow_type', models.CharField(max_length=255)),
                ('profile_workflow_status', models.CharField(max_length=255)),
                ('profile_workflow_label', models.CharField(max_length=255)),
                ('profile_workflow_specification', models.TextField()),
            ],
            options={
                'ordering': ['profile_workflow_name'],
                'verbose_name': 'Profile Workflow',
            },
        ),
        migrations.CreateModel(
            name='SubmissionAgreement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, serialize=False, editable=False, primary_key=True)),
                ('sa_name', models.CharField(max_length=255)),
                ('sa_type', models.CharField(max_length=255)),
                ('sa_status', models.CharField(max_length=255)),
                ('sa_label', models.CharField(max_length=255)),
                ('sa_cm_version', models.CharField(max_length=255)),
                ('sa_cm_release_date', models.CharField(max_length=255)),
                ('sa_cm_change_authority', models.CharField(max_length=255)),
                ('sa_cm_change_description', models.CharField(max_length=255)),
                ('sa_cm_sections_affected', models.CharField(max_length=255)),
                ('sa_producer_organization', models.CharField(max_length=255)),
                ('sa_producer_main_name', models.CharField(max_length=255)),
                ('sa_producer_main_address', models.CharField(max_length=255)),
                ('sa_producer_main_phone', models.CharField(max_length=255)),
                ('sa_producer_main_email', models.CharField(max_length=255)),
                ('sa_producer_main_additional', models.CharField(max_length=255)),
                ('sa_producer_individual_name', models.CharField(max_length=255)),
                ('sa_producer_individual_role', models.CharField(max_length=255)),
                ('sa_producer_individual_phone', models.CharField(max_length=255)),
                ('sa_producer_individual_email', models.CharField(max_length=255)),
                ('sa_producer_individual_additional', models.CharField(max_length=255)),
                ('sa_archivist_organization', models.CharField(max_length=255)),
                ('sa_archivist_main_name', models.CharField(max_length=255)),
                ('sa_archivist_main_address', models.CharField(max_length=255)),
                ('sa_archivist_main_phone', models.CharField(max_length=255)),
                ('sa_archivist_main_email', models.CharField(max_length=255)),
                ('sa_archivist_main_additional', models.CharField(max_length=255)),
                ('sa_archivist_individual_name', models.CharField(max_length=255)),
                ('sa_archivist_individual_role', models.CharField(max_length=255)),
                ('sa_archivist_individual_phone', models.CharField(max_length=255)),
                ('sa_archivist_individual_email', models.CharField(max_length=255)),
                ('sa_archivist_individual_additional', models.CharField(max_length=255)),
                ('sa_designated_community_description', models.CharField(max_length=255)),
                ('sa_designated_community_individual_name', models.CharField(max_length=255)),
                ('sa_designated_community_individual_role', models.CharField(max_length=255)),
                ('sa_designated_community_individual_phone', models.CharField(max_length=255)),
                ('sa_designated_community_individual_email', models.CharField(max_length=255)),
                ('sa_designated_community_individual_additional', models.CharField(max_length=255)),
                ('profile_transfer_project', models.CharField(max_length=255)),
                ('profile_content_type', models.CharField(max_length=255)),
                ('profile_data_selection', models.CharField(max_length=255)),
                ('profile_classification', models.CharField(max_length=255)),
                ('profile_import', models.CharField(max_length=255)),
                ('profile_submit_description', models.CharField(max_length=255)),
                ('profile_sip', models.CharField(max_length=255)),
                ('profile_aip', models.CharField(max_length=255)),
                ('profile_dip', models.CharField(max_length=255)),
                ('profile_workflow', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['sa_name'],
                'verbose_name': 'Submission Agreement',
            },
        ),
    ]
