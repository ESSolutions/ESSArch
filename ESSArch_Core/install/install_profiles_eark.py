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

import json
import os

import django

django.setup()

from django.conf import settings  # noqa isort:skip

from ESSArch_Core.configuration.models import StoragePolicy  # noqa isort:skip
from ESSArch_Core.profiles.models import (  # noqa isort:skip
    SubmissionAgreement,
    Profile,
)


def installProfiles():
    sa = installSubmissionAgreement()

    installProfileTransferProject(sa)
    installProfileContentType(sa)
    installProfileDataSelection(sa)
    installProfileAuthorityInformation(sa)
    installProfileArchivalDescription(sa)
    installProfileImport(sa)
    installProfileSubmitDescription(sa)
    installProfileSIP(sa)
    installProfileAIP(sa)
    installProfileDIP(sa)
    installProfileWorkflow(sa)
    installProfilePreservationMetadata(sa)

    return 0


def installSubmissionAgreement():
    try:
        policy = StoragePolicy.objects.get(policy_name="default")
    except StoragePolicy.DoesNotExist:
        policy = StoragePolicy.objects.first()
        if policy is None:
            raise

    dct = {
        'name': 'SA National Archive and Government EARK',
        'type': 'Standard',
        'status': 'Agreed',
        'label': 'Submission Agreement National Archive x and Government x',
        'policy': policy,
        'archivist_organization': 'National Archive xx',
        'template': [
            {
                "key": "archivist_organization",
                "type": "input",
                "templateOptions": {
                    "type": "text",
                    "required": True,
                    "label": "Archivist Organization"
                },
            }
        ],
    }

    sa, _ = SubmissionAgreement.objects.update_or_create(name=dct['name'], defaults=dct)

    print('Installed submission agreement')

    return sa


def installProfileTransferProject(sa):

    dct = {
        'name': 'Transfer Project Profile EARK',
        'profile_type': 'transfer_project',
        'type': 'Implementation',
        'status': 'Agreed',
        'label': 'Transfer Project Profile 1',
        'template': [
            {
                'key': 'container_format',
                'type': 'select',
                'templateOptions': {
                    'label': 'Container format',
                    'options': [
                        {'name': 'TAR', 'value': 'tar'},
                        {'name': 'ZIP', 'value': 'zip'},
                    ]
                }
            }, {
                "templateOptions": {
                    "disabled": True,
                    "type": "text",
                    "label": "Container format compression",
                    "desc": "xxx",
                },
                "type": "input",
                "key": "container_format_compression"
            }, {
                'key': 'checksum_algorithm',
                'type': 'select',
                'templateOptions': {
                    'label': 'Checksum algorithm',
                    'options': [
                        {'name': 'MD5', 'value': 'MD5'},
                        {'name': 'SHA-256', 'value': 'SHA-256'},
                    ]
                }
            }, {
                "templateOptions": {
                    "type": "email",
                    "label": "Preservation organization receiver email",
                },
                "type": "input",
                "key": "preservation_organization_receiver_email"
            }, {
                "templateOptions": {
                    "type": "url",
                    "label": "Preservation organization receiver url",
                },
                "type": "input",
                "key": "preservation_organization_receiver_url"
            }
        ],
        'specification_data': {
            "archivist_organization": "National Archive xx",
            "archival_institution": "Riksarkivet",
            "archival_type": "document",
            "archival_location": "sweden-stockholm-nacka",
            "storage_policy": "archive policy 1",
            "container_format": "tar",
            "checksum_algorithm": "MD5",
        },
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_transfer_project = profile
    sa.save()

    print('Installed profile transfer project')

    return 0


def installProfileContentType(sa):

    dct = {
        'name': 'CTS EARK SMURF',
        'profile_type': 'content_type',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Content type based on EARK SMURF specification',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_content_type = profile
    sa.save()

    print('Installed profile content type')

    return 0


def installProfileDataSelection(sa):

    dct = {
        'name': 'Data selection of business system xx',
        'profile_type': 'data_selection',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Data selection of business system xx',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_data_selection = profile
    sa.save()

    print('Installed profile data selection')

    return 0


def installProfileAuthorityInformation(sa):

    dct = {
        'name': 'Authority Information 1',
        'profile_type': 'authority_information',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Authority Information 1',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)

    print('Installed profile authority information')

    return 0


def installProfileArchivalDescription(sa):

    dct = {
        'name': 'Archival Description 1',
        'profile_type': 'archival_description',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Archival Description 1',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_archival_description = profile
    sa.save()

    print('Installed profile archival description')

    return 0


def installProfileImport(sa):

    dct = {
        'name': 'Transformation import profile for system xx',
        'profile_type': 'import',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Transformation from system x to specification y',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_import = profile
    sa.save()

    print('Installed profile import')

    return 0


def installProfileSubmitDescription(sa):

    dct = {
        'name': 'Submit description of a single SIP EARK',
        'profile_type': 'submit_description',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Submit description of a single SIP',
        'template': [
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Start Date"
                },
                "type": "datepicker",
                "key": "start_date"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "End Date"
                },
                "type": "datepicker",
                "key": "end_date"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "disabled": True,
                    "label": "Archivist Organization"
                },
                "type": "input",
                "key": "_IP_ARCHIVIST_ORGANIZATION"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator",
                    "required": True,
                },
                "type": "input",
                "key": "creator"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Submitter Organization",
                    "required": True,
                },
                "type": "input",
                "key": "submitter_organization"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Submitter Individual",
                    "required": True,
                },
                "type": "input",
                "key": "submitter_individual"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Producer Organization",
                    "required": True,
                },
                "type": "input",
                "key": "producer_organization"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Producer Individual",
                    "required": True,
                },
                "type": "input",
                "key": "producer_individual"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "IP Owner",
                    "required": True,
                },
                "type": "input",
                "key": "ipowner"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Organization",
                    "required": True,
                },
                "type": "input",
                "key": "preservation_organization"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "System Name",
                    "required": True,
                },
                "type": "input",
                "key": "systemname"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "System Version"
                },
                "type": "input",
                "key": "systemversion"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "System Type"
                },
                "type": "input",
                "key": "systemtype"
            },
        ],
        'specification': json.loads(open(os.path.join(settings.BASE_DIR, 'templates/eark/EARK_SD.json')).read()),
        'specification_data': {
            "profile": "my profile",
            "start_date": "2016-11-10",
            "end_date": "2016-12-20",
            "creator": "the creator",
            "submitter_organization": "the submitter organization",
            "submitter_individual": "the submitter individual",
            "producer_organization": "the submitter organization",
            "producer_individual": "the producer individual",
            "ipowner": "the ip owner",
            "preservation_organization": "the preservation organization",
            "systemname": "the system name",
            "systemversion": "the system version",
            "systemtype": "the system type",
        },
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_submit_description = profile
    sa.save()

    print('Installed profile submit description')

    return 0


def installProfileSIP(sa):

    dct = {
        'name': 'SIP EARK Representations',
        'profile_type': 'sip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'SIP profile for EARK submissions',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to submit description',
        "structure": [
            {
                "use": "mets_file",
                "type": "file",
                "name": "METS.xml"
            },
            {
                "type": "folder",
                "name": "metadata",
                'use': 'metadata',
                "children": [
                    {
                        "type": "folder",
                        "name": "descriptive",
                        "children": [
                            {
                                "use": "archival_description_file",
                                "type": "file",
                                "name": "ead.xml"
                            },
                            {
                                "use": "authoritive_information_file",
                                "type": "file",
                                "name": "eaccpf.xml"
                            }
                        ]
                    },
                    {
                        "type": "folder",
                        "name": "preservation",
                        "children": [
                            {
                                "use": "preservation_description_file",
                                "type": "file",
                                "name": "premis.xml"
                            }
                        ]
                    },
                    {
                        "type": "folder",
                        "name": "other",
                        "children": [
                            {
                                "use": "events_file",
                                "type": "file",
                                "name": "{{_OBJID}}_ipevents.xml"
                            }
                        ]
                    }
                ]
            },
            {
                "type": "folder",
                "name": "representations",
                "children": [
                    {
                        "type": "folder",
                        "name": "rep-001",
                        "children": [
                            {
                                "type": "folder",
                                "name": "data",
                            }
                        ]
                    }
                ]
            },
            {
                "type": "folder",
                "name": "schemas",
                "children": [
                    {
                        "use": "xsd_files",
                        "type": "file",
                        "name": "xsd_files"
                    }
                ]
            },
            {
                "type": "folder",
                "name": "documentation",
                "children": []
            }
        ],
        'template': [
            {
                "key": "mets_type",
                "type": "select",
                "defaultValue": "Personnel",
                "templateOptions": {
                    "label": "Content Type",
                    "options": [
                        {
                            "name": "Electronic Record Management System",
                            "value": "ERMS"
                        },
                        {
                            "name": "Personnel system",
                            "value": "Personnel"
                        },
                        {
                            "name": "Medical record(s)",
                            "value": "Medical record"
                        },
                        {
                            "name": "Economics",
                            "value": "Economics systems"
                        },
                        {
                            "name": "Databases",
                            "value": "Databases"
                        },
                        {
                            "name": "Webpages",
                            "value": "Webpages"
                        },
                        {
                            "name": "Geografical Information Systems",
                            "value": "GIS"
                        },
                        {
                            "name": "No specification",
                            "value": "No specification"
                        },
                        {
                            "name": "Archival Information Collection",
                            "value": "AIC"
                        },
                        {
                            "name": "Archival Information",
                            "value": "Archival Information"
                        },
                        {
                            "name": "Unstructured",
                            "value": "Unstructured"
                        },
                        {
                            "name": "Single records",
                            "value": "Single records"
                        },
                        {
                            "name": "Publication",
                            "value": "Publication"
                        },
                    ]
                },
            },
            {
                "key": "RECORDSTATUS",
                "type": "select",
                "templateOptions": {
                    "label": "Record Status",
                    "options": [
                        {
                            "name": "SUPPLEMENT",
                            "value": "SUPPLEMENT"
                        },
                        {
                            "name": "REPLACEMENT",
                            "value": "REPLACEMENT"
                        },
                        {
                            "name": "NEW",
                            "value": "NEW"
                        },
                        {
                            "name": "TEST",
                            "value": "TEST"
                        },
                        {
                            "name": "VERSION",
                            "value": "VERSION"
                        },
                        {
                            "name": "OTHER",
                            "value": "OTHER"
                        },
                    ]
                },
            },
            {
                "templateOptions": {
                    "type": "text",
                    "disabled": True,
                    "label": "Archivist Organization"
                },
                "type": "input",
                "key": "_IP_ARCHIVIST_ORGANIZATION"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Archivist Organization Note"
                },
                "type": "input",
                "key": "archivist_organization_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Organization",
                    "required": True,
                },
                "type": "input",
                "key": "creator_organization_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Organization Note"
                },
                "type": "input",
                "key": "creator_organization_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Software",
                    "required": True,
                },
                "type": "input",
                "key": "creator_software_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Software Note"
                },
                "type": "input",
                "key": "creator_software_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Organization",
                    "required": True,
                },
                "type": "input",
                "key": "preservation_organization_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Organization Note"
                },
                "type": "input",
                "key": "preservation_organization_note"
            },
        ],
        'specification': json.loads(open(os.path.join(settings.BASE_DIR, 'templates/eark/EARK_SIP_REP.json')).read()),
        'specification_data': {
            "mets_type": "ERMS",
            "RECORDSTATUS": "NEW",
            "archivist_organization_note": "Archivist Organization 1 Note",
            "creator_organization_name": "Creator Organization 1",
            "creator_organization_note": "Creator Organization 1 Note",
            "creator_software_name": "Creator Software 1",
            "creator_software_note": "Creator Software 1 Note",
            "preservation_organization_name": "Preservation Organization 1",
            "preservation_organization_note": "Preservation Organization 1 Note",
        }
    }

    dct2 = {
        'name': 'SIP EARK',
        'profile_type': 'sip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'SIP profile for EARK submissions',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to submit description',
        "structure": [
            {
                "use": "mets_file",
                "type": "file",
                "name": "METS.xml"
            },
            {
                "type": "folder",
                "name": "metadata",
                'use': 'metadata',
                "children": [
                    {
                        "type": "folder",
                        "name": "descriptive",
                        "children": [
                            {
                                "use": "archival_description_file",
                                "type": "file",
                                "name": "ead.xml"
                            },
                            {
                                "use": "authoritive_information_file",
                                "type": "file",
                                "name": "eaccpf.xml"
                            }
                        ]
                    },
                    {
                        "type": "folder",
                        "name": "preservation",
                        "children": [
                            {
                                "use": "preservation_description_file",
                                "type": "file",
                                "name": "premis.xml"
                            }
                        ]
                    },
                    {
                        "type": "folder",
                        "name": "other",
                        "children": []
                    }
                ]
            },
            {
                "type": "folder",
                "name": "representations",
                "children": [
                    {
                        "type": "folder",
                        "name": "rep-001",
                        "children": [
                            {
                                "type": "folder",
                                "name": "data",
                            }
                        ]
                    }
                ]
            },
            {
                "type": "folder",
                "name": "schemas",
                "children": [
                    {
                        "use": "xsd_files",
                        "type": "file",
                        "name": "xsd_files"
                    }
                ]
            },
            {
                "type": "folder",
                "name": "documentation",
                "children": []
            }
        ],
        'template': [
            {
                "key": "mets_type",
                "type": "select",
                "templateOptions": {
                    "label": "Content Type",
                    "options": [
                        {
                            "name": "Electronic Record Management System",
                            "value": "ERMS"
                        },
                        {
                            "name": "Personnel system",
                            "value": "Personnel"
                        },
                        {
                            "name": "Medical record(s)",
                            "value": "Medical record"
                        },
                        {
                            "name": "Economics",
                            "value": "Economics systems"
                        },
                        {
                            "name": "Databases",
                            "value": "Databases"
                        },
                        {
                            "name": "Webpages",
                            "value": "Webpages"
                        },
                        {
                            "name": "Geografical Information Systems",
                            "value": "GIS"
                        },
                        {
                            "name": "No specification",
                            "value": "No specification"
                        },
                        {
                            "name": "Archival Information Collection",
                            "value": "AIC"
                        },
                        {
                            "name": "Archival Information",
                            "value": "Archival Information"
                        },
                        {
                            "name": "Unstructured",
                            "value": "Unstructured"
                        },
                        {
                            "name": "Single records",
                            "value": "Single records"
                        },
                        {
                            "name": "Publication",
                            "value": "Publication"
                        },
                    ]
                },
            },
            {
                "key": "RECORDSTATUS",
                "type": "select",
                "templateOptions": {
                    "label": "Record Status",
                    "options": [
                        {
                            "name": "SUPPLEMENT",
                            "value": "SUPPLEMENT"
                        },
                        {
                            "name": "REPLACEMENT",
                            "value": "REPLACEMENT"
                        },
                        {
                            "name": "NEW",
                            "value": "NEW"
                        },
                        {
                            "name": "TEST",
                            "value": "TEST"
                        },
                        {
                            "name": "VERSION",
                            "value": "VERSION"
                        },
                        {
                            "name": "OTHER",
                            "value": "OTHER"
                        },
                    ]
                },
            },
            {
                "templateOptions": {
                    "type": "text",
                    "disabled": True,
                    "label": "Archivist Organization"
                },
                "type": "input",
                "key": "_IP_ARCHIVIST_ORGANIZATION"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Archivist Organization Note"
                },
                "type": "input",
                "key": "archivist_organization_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Organization",
                    "required": True,
                },
                "type": "input",
                "key": "creator_organization_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Organization Note"
                },
                "type": "input",
                "key": "creator_organization_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Software",
                    "required": True,
                },
                "type": "input",
                "key": "creator_software_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Software Note"
                },
                "type": "input",
                "key": "creator_software_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Organization",
                    "required": True,
                },
                "type": "input",
                "key": "preservation_organization_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Organization Note"
                },
                "type": "input",
                "key": "preservation_organization_note"
            },
        ],
        'specification': json.loads(open(os.path.join(settings.BASE_DIR, 'templates/eark/EARK_SIP.json')).read()),
        'specification_data': {
            "mets_type": "ERMS",
            "RECORDSTATUS": "NEW",
            "archivist_organization_note": "Archivist Organization 1 Note",
            "creator_organization_name": "Creator Organization 1",
            "creator_organization_note": "Creator Organization 1 Note",
            "creator_software_name": "Creator Software 1",
            "creator_software_note": "Creator Software 1 Note",
            "preservation_organization_name": "Preservation Organization 1",
            "preservation_organization_note": "Preservation Organization 1 Note",
        }
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    profile2, _ = Profile.objects.update_or_create(name=dct2['name'], defaults=dct2)
    sa.profile_sip = profile
    sa.save()

    print('Installed profile SIP')

    return 0


def installProfileAIP(sa):

    dct = {
        'name': 'AIP EARK',
        'profile_type': 'aip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'AIP profile for EARK Packages',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to submit description',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_aip = profile
    sa.save()

    print('Installed profile AIP')

    return 0


def installProfileDIP(sa):

    dct = {
        'name': 'DIP EARK',
        'profile_type': 'dip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'DIP profile for EARK Packages',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to submit description',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_dip = profile
    sa.save()

    print('Installed profile DIP')

    return 0


def installProfileWorkflow(sa):

    dct = {
        'name': 'Workflow xx for Pre-Ingest',
        'profile_type': 'workflow',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Workflow Create SIP for Pre-Ingest',
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_workflow = profile
    sa.save()

    print('Installed profile workflow')

    return 0


def installProfilePreservationMetadata(sa):

    dct = {
        'name': 'Preservation profile EARK',
        'profile_type': 'preservation_metadata',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Preservation profile for AIP xxyy',
        'template': [
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Agent Identifier Value"
                },
                "type": "input",
                "defaultValue": "ESSArch_Preservation_Platform",
                "key": "agent_identifier_value"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Agent Name"
                },
                "type": "input",
                "defaultValue": "ESSArch",
                "key": "agent_name"
            },
            {
                "templateOptions": {
                    "disabled": True,
                    "type": "text",
                    "label": "Container Format"
                },
                "hidden": True,
                "type": "input",
                "key": "$transfer_project__container_format",
            }
        ],
        'specification': json.loads(open(os.path.join(settings.BASE_DIR, 'templates/eark/EARK_PREMIS.json')).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_preservation_metadata = profile
    sa.save()

    print('Installed profile preservation metadata')

    return 0


if __name__ == '__main__':
    installProfiles()
