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

from ESSArch_Core._version import get_versions

django.setup()

from django.conf import settings  # noqa isort:skip

from ESSArch_Core.profiles.models import (  # noqa isort:skip
    SubmissionAgreement,
    Profile,
)


def installProfiles():
    sa = installSA()                # Submission Agreement EARK SIP/AIP/DIP

    installProfileSIP(sa)           # EARK Submission Information Package Profile
    installProfileAIP(sa)           # EARK Archival Information Package Profile
    installProfileDIP(sa)           # EARK Dissemination Information Package Profile

#    installProfileCITS(sa)          # Content Information Type Specification Profile

    installProfileSD(sa)             # EARK Submit Description Profile
    installProfileTP(sa)            # EARK Transfer Project Profile
    installProfileAICD(sa)          # EARK Archival Information Collection Description Profile
    installProfileAIPD(sa)          # EARK Archival Information Package Description Profile
    installProfilePM(sa)            # EARK Preservation Metadata Profile
    installProfileWF(sa)            # EARK Workflow Profile

    return 0


def installSA():

    dct = {
        'name': 'SA Archive and Organization (EARK)',
        'published': True,
        'type': 'Standard',
        'status': 'Draft',
        'label': 'Submission Agreement Archive x and Organization y',
        'archivist_organization': 'Archival Creator Organization xx',
        'template': [
            {
                "key": "_IP_ARCHIVIST_ORGANIZATION",
                "type": "input",
                "templateOptions": {
                    "type": "text",
                    "required": True,
                    "disabled": True,
                    "label": "Archival Creator Organization"
                },
            },
            {
                "key": "archivist_organization_note",
                "type": "input",
                "defaultValue": "Org:123456-1234",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Identification Code"
                },
            },
            {
                "key": "preservation_organization_name",
                "type": "input",
                "defaultValue": "Preservation Organization",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization",
                },
            },
            {
                "key": "preservation_organization_note",
                "type": "input",
                "defaultValue": "Preservation Organization IDC",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization Identification Code"
                },
            },
            {
                "key": "creator_organization_name",
                "type": "input",
                "defaultValue": "Submitter Organization",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization",
                },
            },
            {
                "key": "creator_organization_note",
                "type": "input",
                "defaultValue": "Org:654321:4321",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization Identification Code"
                },
            },
            {
                "key": "creator_individual_name",
                "type": "input",
                "defaultValue": "Name of the contact person",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Contact Person",
                },
            },
            {
                "key": "creator_individual_note",
                "type": "input",
                "defaultValue": "E-mail, phone etc",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Contact Person Details",
                },
            },
            {
                "key": "creator_software_name",
                "type": "input",
                "defaultValue": "ESSArch",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Software",
                },
            },
            {
                "key": "creator_software_note",
                "type": "input",
                "defaultValue": get_versions()['version'],
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Software Version"
                },
            },
        ],
    }

    sa, _ = SubmissionAgreement.objects.update_or_create(name=dct['name'], defaults=dct)

    print('Installed Submission Agreement (EARK)')

    return sa


def installProfileSIP(sa):

    dct = {
        'name': 'SIP (EARK)',
        'profile_type': 'sip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Submission Information Package profile',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to Submission Agreement',
        'structure': [
            {
                'type': 'file',
                'name': 'mets.xml',
                'use': 'mets_file',
            },
            {
                'type': 'folder',
                'name': 'metadata',
                'use': 'metadata',
                'children': [
                    {
                        'type': 'folder',
                        'name': 'descriptive',
                        'use': 'descriptive',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'ead.xml',
                                'use': 'archival_description_file',
                            },
                            {
                                'type': 'file',
                                'name': 'eac.xml',
                                'use': 'authoritative_information_file',
                            }
                        ],
                    },
                    {
                        'type': 'folder',
                        'name': 'other',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'ipevents.xml',
                                'use': 'events_file',
                            }
                        ],
                    },
                    {
                        'type': 'folder',
                        'name': 'preservation',
                        'use': 'preservation',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'premis.xml',
                                'use': 'preservation_description_file',
                            }
                        ],
                    },
                ]
            },
            {
                'type': 'folder',
                'name': 'representations',
                'use': 'representations',
                'children': [
                    {
                        'type': 'folder',
                        'name': 'rep1',
                        'use': 'rep1',
                        'children': [
                            {
                                'type': 'folder',
                                'name': 'metadata',
                                'use': 'metadata',
                                'children': [
                                    {
                                        'type': 'folder',
                                        'name': 'preservation',
                                        'use': 'preservation',
                                    }
                                ],
                            },
                            {
                                'type': 'folder',
                                'name': 'data',
                                'use': 'data',
                                'children': []
                            },
                            {
                                'type': 'folder',
                                'name': 'documentation',
                                'use': 'documentation',
                                'children': []
                            },
                        ],
                    }
                ],
            },
            {
                'type': 'folder',
                'name': 'schemas',
                'use': 'schemas',
                'children': [
                    {
                        'type': 'file',
                        'name': 'xsd files',
                        'use': 'xsd_files',
                    }
                ],
            },
            {
                'type': 'folder',
                'name': 'documentation',
                'use': 'documentation',
                'children': []
            },
        ],
        'template': [
            {
                "key": "_IP_ARCHIVIST_ORGANIZATION",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Organization"
                },
            },
            {
                "key": "archivist_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Identification Code"
                },
            },
            {
                "key": "preservation_organization_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization",
                },
            },
            {
                "key": "preservation_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization Identification Code"
                },
            },
            {
                "key": "creator_organization_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization",
                },
            },
            {
                "key": "creator_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization Identification Code"
                },
            },
            {
                "key": "creator_individual_name",
                "type": "input",
                "defaultValue": "Name of the contact person",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Contact Person",
                },
            },
            {
                "key": "creator_individual_note",
                "type": "input",
                "defaultValue": "E-mail, phone etc",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Contact Person Details",
                },
            },
            {
                "key": "mets_type",
                "type": "select",
                "defaultValue": "Other",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "label": "Content Category (EARK)",
                    "options": [
                        {
                            "name": "Textual works – Print",
                            "value": "Textual works – Print",
                            'definition': "Books, musical compositions, etc."
                        },
                        {
                            "name": "Textual works – Digital",
                            "value": "Textual works – Digital",
                            'definition': "Electronic books, etc"
                        },
                        {
                            "name": "Textual works – Electronic Serials",
                            "value": "Textual works – Electronic Serials",
                            'definition': ""
                        },
                        {
                            "name": "Digital Musical Composition (score-based representations)",
                            "value": "Digital Musical Composition (score-based representations)",
                            'definition': ""
                        },
                        {
                            "name": "Photographs – Print",
                            "value": "Photographs – Print",
                            'definition': ""
                        },
                        {
                            "name": "Photographs – Digital",
                            "value": "Photographs – Digital",
                            'definition': ""
                        },
                        {
                            "name": "Other Graphic Images – Print",
                            "value": "Other Graphic Images – Print",
                            'definition': "Posters, architectural drawings, postcards, maps, fine prints, etc."
                        },
                        {
                            "name": "Other Graphic Images – Digital",
                            "value": "Other Graphic Images – Digital",
                            'definition': ""
                        },
                        {
                            "name": "Microforms",
                            "value": "Microforms",
                            'definition': ""
                        },
                        {
                            "name": "Audio – On Tangible Medium (digital or analog)",
                            "value": "Audio – On Tangible Medium (digital or analog)",
                            'definition': ""
                        },
                        {
                            "name": "Audio – Media-independent (digital)",
                            "value": "Audio – Media-independent (digital)",
                            'definition': ""
                        },
                        {
                            "name": "Motion Pictures – Digital and Physical Media",
                            "value": "Motion Pictures – Digital and Physical Media",
                            'definition': "Theatrically released films"
                        },
                        {
                            "name": "Video – File-based and Physical Media",
                            "value": "Video – File-based and Physical Media",
                            'definition': ""
                        },
                        {
                            "name": "Software",
                            "value": "Software",
                            'definition': "Software, electronic gaming and learning"
                        },
                        {
                            "name": "Datasets",
                            "value": "Datasets",
                            'definition': "Data encoded in a defined structure"
                        },
                        {
                            "name": "Geospatial Data",
                            "value": "Geospatial Data",
                            'definition': ""
                        },
                        {
                            "name": "Databases",
                            "value": "Databases",
                            'definition': ""
                        },
                        {
                            "name": "Websites",
                            "value": "Websites",
                            'definition': "Archived web content"
                        },
                        {
                            "name": "Collection",
                            "value": "Collection",
                            'definition': "An aggregation of resources"
                        },
                        {
                            "name": "Event",
                            "value": "Event",
                            'definition': "A non-persistent, time-based occurrence, e.g. exhibition, webcast, etc"
                        },
                        {
                            "name": "Interactive resource",
                            "value": "Interactive resource",
                            'definition': "A resource requiring interaction from the user to be "
                                          "understood, executed, or experienced."
                        },
                        {
                            "name": "Physical object",
                            "value": "Physical object",
                            'definition': "An inanimate, three-dimensional object or substance"
                        },
                        {
                            "name": "Service",
                            "value": "Service",
                            'definition': "A system that provides one or more functions"
                        },
                        {
                            "name": "Mixed",
                            "value": "Mixed",
                            'definition': "The package contains a mix of content types"
                        },
                        {
                            "name": "Other",
                            "value": "Other",
                            'definition': "A term other than present in the vocabulary is used"
                        },
                    ]
                },
            },
            {
                "key": "mets_othertype",
                "type": "select",
                "defaultValue": "Unstructured",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Other Content Category",
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
                "key": "CONTENTINFORMATIONTYPE",
                "type": "select",
                "defaultValue": "OTHER",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Content Information Type (EARK)",
                    "options": [
                        {
                            "name": "ERMS",
                            "value": "ERMS"
                        },
                        {
                            "name": "SIARD1",
                            "value": "SIARD1"
                        },
                        {
                            "name": "SIARD2",
                            "value": "SIARD2"
                        },
                        {
                            "name": "SIARDDK",
                            "value": "SIARDDK"
                        },
                        {
                            "name": "GeoData",
                            "value": "GeoData"
                        },
                        {
                            "name": "MIXED",
                            "value": "MIXED"
                        },
                        {
                            "name": "OTHER",
                            "value": "OTHER"
                        },
                    ]
                },
            },
            {
                "key": "OTHERCONTENTINFORMATIONTYPE",
                "type": "select",
                "defaultValue": "Unstructured",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Other Content Information Type",
                    "options": [
                        {
                            "name": "FGS Personal",
                            "value": "Personnel"
                        },
                        {
                            "name": "FGS Ärende",
                            "value": "ERMS"
                        },
                        {
                            "name": "FGS Databas",
                            "value": "ADDML"
                        },
                        {
                            "name": "Unstructured",
                            "value": "Unstructured"
                        },
                    ]
                },
            },
            {
                "key": "creator_software_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Software",
                },
            },
            {
                "key": "creator_software_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Software Version"
                },
            },
            {
                "key": "RECORDSTATUS",
                "type": "select",
                "defaultValue": "NEW",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Information Package Status",
                    "options": [
                        {
                            "name": "NEW",
                            "value": "NEW"
                        },
                        {
                            "name": "SUPPLEMENT",
                            "value": "SUPPLEMENT"
                        },
                        {
                            "name": "REPLACEMENT",
                            "value": "REPLACEMENT"
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
                            "name": "DELETE",
                            "value": "DELETE"
                        },
                        {
                            "name": "OTHER",
                            "value": "OTHER"
                        },
                    ]
                },
            },
            {
                "key": "allow_unknown_file_types",
                "type": "select",
                "defaultValue": True,
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Allow unknown file types in IP",
                    "options": [
                        {"name": "Yes", "value": True},
                        {"name": "No", "value": False},
                    ],
                },
            },
        ],
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_SIP_v202.json')
        ).read()),
    }

    sa.profile_sip, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    print('Installed profile SIP (EARK)')

    return 0


def installProfileAIP(sa):

    dct = {
        'name': 'AIP (EARK)',
        'profile_type': 'aip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Archival Information Package profile',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to Submission Agreement',
        'structure': [
            {
                'type': 'file',
                'name': 'mets.xml',
                'use': 'mets_file',
            },
            {
                'type': 'folder',
                'name': 'metadata',
                'use': 'metadata',
                'children': [
                    {
                        'type': 'folder',
                        'name': 'descriptive',
                        'use': 'descriptive',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'ead.xml',
                                'use': 'archival_description_file',
                            },
                            {
                                'type': 'file',
                                'name': 'eac.xml',
                                'use': 'authoritative_information_file',
                            }
                        ],
                    },
                    {
                        'type': 'folder',
                        'name': 'other',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'ipevents.xml',
                                'use': 'events_file',
                            }
                        ],
                    },
                    {
                        'type': 'folder',
                        'name': 'preservation',
                        'use': 'preservation',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'premis.xml',
                                'use': 'preservation_description_file',
                            }
                        ],
                    },
                ]
            },
            {
                'type': 'folder',
                'name': 'schemas',
                'use': 'schemas',
                'children': [
                    {
                        'type': 'file',
                        'name': 'xsd files',
                        'use': 'xsd_files',
                    }
                ],
            },
            {
                'type': 'folder',
                'name': 'documentation',
                'use': 'documentation',
                'children': []
            },
            {
                'type': 'folder',
                'name': 'submission',
                'use': 'submission',
                'children': [
                    {
                        'type': 'folder',
                        'name': '{{INNER_IP_OBJID}}',
                        'use': 'sip',
                        'children': [],
                    }
                ]
            },
        ],
        'template': [
            {
                "key": "_IP_ARCHIVIST_ORGANIZATION",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Organization"
                },
            },
            {
                "key": "archivist_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Identification Code"
                },
            },
            {
                "key": "preservation_organization_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization",
                },
            },
            {
                "key": "preservation_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization Identification Code"
                },
            },
            {
                "key": "creator_organization_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization",
                },
            },
            {
                "key": "creator_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization Identification Code"
                },
            },
            {
                "key": "creator_individual_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Contact Person",
                },
            },
            {
                "key": "creator_individual_note",
                "type": "input",
                "templateOptions": {
                    "required": False,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Contact Person Details",
                },
            },
            {
                "key": "creator_software_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Software",
                },
            },
            {
                "key": "creator_software_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Software Version"
                },
            },
            {
                "key": "allow_unknown_file_types",
                "type": "select",
                "defaultValue": True,
                "templateOptions": {
                    "label": "Allow unknown file types",
                    "options": [
                        {"name": "Yes", "value": True},
                        {"name": "No", "value": False},
                    ],
                },
            },
            {
                "key": "allow_encrypted_files",
                "type": "select",
                "defaultValue": False,
                "templateOptions": {
                    "label": "Allow encrypted files",
                    "options": [
                        {"name": "Yes", "value": True},
                        {"name": "No", "value": False},
                    ],
                },
            },
            {
                "key": "index_files",
                "type": "select",
                "defaultValue": True,
                "templateOptions": {
                    "label": "Index files",
                    "options": [
                        {"name": "Yes", "value": True},
                        {"name": "No", "value": False},
                    ],
                }
            },
        ],
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_AIP_v201.json')
        ).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_aip = profile
    sa.save()

    print('Installed profile AIP (EARK)')

    return 0


def installProfileDIP(sa):

    dct = {
        'name': 'DIP (EARK)',
        'profile_type': 'dip',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Dissemination Information Package profile',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to Submission Agreement',
        'structure': [
            {
                'type': 'file',
                'name': 'mets.xml',
                'use': 'mets_file',
            },
            {
                'type': 'folder',
                'name': 'metadata',
                'use': 'metadata',
                'children': [
                    {
                        'type': 'folder',
                        'name': 'descriptive',
                        'use': 'descriptive',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'ead.xml',
                                'use': 'archival_description_file',
                            },
                            {
                                'type': 'file',
                                'name': 'eac.xml',
                                'use': 'authoritative_information_file',
                            }
                        ],
                    },
                    {
                        'type': 'folder',
                        'name': 'other',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'ipevents.xml',
                                'use': 'events_file',
                            }
                        ],
                    },
                    {
                        'type': 'folder',
                        'name': 'preservation',
                        'use': 'preservation',
                        'children': [
                            {
                                'type': 'file',
                                'name': 'premis.xml',
                                'use': 'preservation_description_file',
                            }
                        ],
                    },
                ]
            },
            {
                'type': 'folder',
                'name': 'representations',
                'use': 'representations',
                'children': [
                    {
                        'type': 'folder',
                        'name': 'rep1',
                        'use': 'rep1',
                        'children': [
                            {
                                'type': 'folder',
                                'name': 'metadata',
                                'use': 'metadata',
                                'children': [
                                    {
                                        'type': 'folder',
                                        'name': 'preservation',
                                        'use': 'preservation',
                                    }
                                ],
                            },
                            {
                                'type': 'folder',
                                'name': 'data',
                                'use': 'data',
                                'children': []
                            },
                            {
                                'type': 'folder',
                                'name': 'documentation',
                                'use': 'documentation',
                                'children': []
                            },
                        ],
                    }
                ],
            },
            {
                'type': 'folder',
                'name': 'schemas',
                'use': 'schemas',
                'children': [
                    {
                        'type': 'file',
                        'name': 'xsd files',
                        'use': 'xsd_files',
                    }
                ],
            },
            {
                'type': 'folder',
                'name': 'documentation',
                'use': 'documentation',
                'children': []
            },
        ],
        'template': [
            {
                "key": "_IP_ARCHIVIST_ORGANIZATION",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Organization"
                },
            },
            {
                "key": "archivist_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Archival Creator Identification Code"
                },
            },
            {
                "key": "preservation_organization_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization",
                },
            },
            {
                "key": "preservation_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Preservation Organization Identification Code"
                },
            },
            {
                "key": "creator_organization_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization",
                },
            },
            {
                "key": "creator_organization_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": True,
                    "type": "text",
                    "label": "Creator Organization Identification Code"
                },
            },
            {
                "key": "creator_individual_name",
                "type": "input",
                "defaultValue": "Name of the contact person",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Contact Person",
                },
            },
            {
                "key": "creator_individual_note",
                "type": "input",
                "defaultValue": "E-mail, phone etc",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Contact Person Details",
                },
            },
            {
                "key": "mets_type",
                "type": "select",
                "defaultValue": "Other",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "label": "Content Category (EARK)",
                    "options": [
                        {
                            "name": "Textual works – Print",
                            "value": "Textual works – Print",
                            'definition': "Books, musical compositions, etc."
                        },
                        {
                            "name": "Textual works – Digital",
                            "value": "Textual works – Digital",
                            'definition': "Electronic books, etc"
                        },
                        {
                            "name": "Textual works – Electronic Serials",
                            "value": "Textual works – Electronic Serials",
                            'definition': ""
                        },
                        {
                            "name": "Digital Musical Composition (score-based representations)",
                            "value": "Digital Musical Composition (score-based representations)",
                            'definition': ""
                        },
                        {
                            "name": "Photographs – Print",
                            "value": "Photographs – Print",
                            'definition': ""
                        },
                        {
                            "name": "Photographs – Digital",
                            "value": "Photographs – Digital",
                            'definition': ""
                        },
                        {
                            "name": "Other Graphic Images – Print",
                            "value": "Other Graphic Images – Print",
                            'definition': "Posters, architectural drawings, postcards, maps, fine prints, etc."
                        },
                        {
                            "name": "Other Graphic Images – Digital",
                            "value": "Other Graphic Images – Digital",
                            'definition': ""
                        },
                        {
                            "name": "Microforms",
                            "value": "Microforms",
                            'definition': ""
                        },
                        {
                            "name": "Audio – On Tangible Medium (digital or analog)",
                            "value": "Audio – On Tangible Medium (digital or analog)",
                            'definition': ""
                        },
                        {
                            "name": "Audio – Media-independent (digital)",
                            "value": "Audio – Media-independent (digital)",
                            'definition': ""
                        },
                        {
                            "name": "Motion Pictures – Digital and Physical Media",
                            "value": "Motion Pictures – Digital and Physical Media",
                            'definition': "Theatrically released films"
                        },
                        {
                            "name": "Video – File-based and Physical Media",
                            "value": "Video – File-based and Physical Media",
                            'definition': ""
                        },
                        {
                            "name": "Software",
                            "value": "Software",
                            'definition': "Software, electronic gaming and learning"
                        },
                        {
                            "name": "Datasets",
                            "value": "Datasets",
                            'definition': "Data encoded in a defined structure"
                        },
                        {
                            "name": "Geospatial Data",
                            "value": "Geospatial Data",
                            'definition': ""
                        },
                        {
                            "name": "Databases",
                            "value": "Databases",
                            'definition': ""
                        },
                        {
                            "name": "Websites",
                            "value": "Websites",
                            'definition': "Archived web content"
                        },
                        {
                            "name": "Collection",
                            "value": "Collection",
                            'definition': "An aggregation of resources"
                        },
                        {
                            "name": "Event",
                            "value": "Event",
                            'definition': "A non-persistent, time-based occurrence, e.g. exhibition, webcast, etc"
                        },
                        {
                            "name": "Interactive resource",
                            "value": "Interactive resource",
                            'definition': "A resource requiring interaction from the user to be "
                                          "understood, executed, or experienced."
                        },
                        {
                            "name": "Physical object",
                            "value": "Physical object",
                            'definition': "An inanimate, three-dimensional object or substance"
                        },
                        {
                            "name": "Service",
                            "value": "Service",
                            'definition': "A system that provides one or more functions"
                        },
                        {
                            "name": "Mixed",
                            "value": "Mixed",
                            'definition': "The package contains a mix of content types"
                        },
                        {
                            "name": "Other",
                            "value": "Other",
                            'definition': "A term other than present in the vocabulary is used"
                        },
                    ]
                },
            },
            {
                "key": "mets_othertype",
                "type": "select",
                "defaultValue": "Unstructured",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Other Content Category",
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
                "key": "CONTENTINFORMATIONTYPE",
                "type": "select",
                "defaultValue": "OTHER",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Content Information Type (EARK)",
                    "options": [
                        {
                            "name": "ERMS",
                            "value": "ERMS"
                        },
                        {
                            "name": "SIARD1",
                            "value": "SIARD1"
                        },
                        {
                            "name": "SIARD2",
                            "value": "SIARD2"
                        },
                        {
                            "name": "SIARDDK",
                            "value": "SIARDDK"
                        },
                        {
                            "name": "GeoData",
                            "value": "GeoData"
                        },
                        {
                            "name": "MIXED",
                            "value": "MIXED"
                        },
                        {
                            "name": "OTHER",
                            "value": "OTHER"
                        },
                    ]
                },
            },
            {
                "key": "OTHERCONTENTINFORMATIONTYPE",
                "type": "select",
                "defaultValue": "Unstructured",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Other Content Information Type",
                    "options": [
                        {
                            "name": "FGS Personal",
                            "value": "Personnel"
                        },
                        {
                            "name": "FGS Ärende",
                            "value": "ERMS"
                        },
                        {
                            "name": "FGS Databas",
                            "value": "ADDML"
                        },
                        {
                            "name": "Unstructured",
                            "value": "Unstructured"
                        },
                    ]
                },
            },
            {
                "key": "creator_software_name",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Software",
                },
            },
            {
                "key": "creator_software_note",
                "type": "input",
                "templateOptions": {
                    "required": True,
                    "disabled": False,
                    "type": "text",
                    "label": "Creator Software Version"
                },
            },
            {
                "key": "RECORDSTATUS",
                "type": "select",
                "defaultValue": "NEW",
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Information Package Status",
                    "options": [
                        {
                            "name": "NEW",
                            "value": "NEW"
                        },
                        {
                            "name": "SUPPLEMENT",
                            "value": "SUPPLEMENT"
                        },
                        {
                            "name": "REPLACEMENT",
                            "value": "REPLACEMENT"
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
                            "name": "DELETE",
                            "value": "DELETE"
                        },
                        {
                            "name": "OTHER",
                            "value": "OTHER"
                        },
                    ]
                },
            },
            {
                "key": "allow_unknown_file_types",
                "type": "select",
                "defaultValue": True,
                "templateOptions": {
                    "required": False,
                    "disabled": False,
                    "label": "Allow unknown file types in IP",
                    "options": [
                        {"name": "Yes", "value": True},
                        {"name": "No", "value": False},
                    ],
                },
            },
        ],
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_DIP_v202.json')
        ).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_dip = profile
    sa.save()

    print('Installed profile DIP (EARK)')

    return 0


def installProfileCITS(sa):

    dct = {
        'name': 'CITS ERMS (EARK)',
        'profile_type': 'content_type',
        'type': 'content_type',
        'status': 'Draft',
        'label': 'Content Information Type Specification profile',
        'specification': {
            'name': 'eark_erms'
        }
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_content_type = profile
    sa.save()

    print('Installed profile content type (EARK)')

    return 0


def installProfileSD(sa):
    dct = {
        'name': 'SD (EARK)',
        'profile_type': 'submit_description',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Submit description profile',
        'template': [
            {
                "key": "_IP_ARCHIVIST_ORGANIZATION",
                "type": "input",
                "templateOptions": {
                    "type": "text",
                    "required": True,
                    "disabled": True,
                    "label": "Archival Creator Organization"
                },
            },
            {
                "key": "preservation_organization_name",
                "type": "input",
                "templateOptions": {
                    "type": "text",
                    "required": True,
                    "disabled": True,
                    "label": "Preservation Organization"
                },
            },
            {
                "key": "creator_organization_name",
                "type": "input",
                "templateOptions": {
                    "type": "text",
                    "required": True,
                    "disabled": True,
                    "label": "Creator Organization"
                },
            },
            {
                'key': 'checksum_algorithm',
                'type': 'select',
                'defaultValue': 'MD5',
                'templateOptions': {
                    'label': 'Checksum algorithm',
                    'options': [
                        {'name': 'MD5', 'value': 'MD5'},
                        {'name': 'SHA-256', 'value': 'SHA-256'},
                    ]
                }
            },
            {
                'key': 'container_format',
                'type': 'select',
                'defaultValue': 'tar',
                'templateOptions': {
                    'label': 'Container format',
                    'options': [
                        {'name': 'TAR', 'value': 'tar'},
                        {'name': 'ZIP', 'value': 'zip'},
                    ]
                }
            },
            {
                "key": "container_format_compression",
                "templateOptions": {
                    "label": "Container format compression",
                    "options": [
                        {
                            "name": "Yes",
                            "value": True
                        },
                        {
                            "name": "No",
                            "value": False
                        }
                    ]
                },
                "defaultValue": False,
                "type": "select"
            },
            {
                "templateOptions": {
                    "type": "email",
                    "label": "Preservation organization receiver email",
                },
                "type": "input",
                "key": "preservation_organization_receiver_email"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "remote": "",
                    "label": "Preservation organization receiver url (empty for local)",
                },
                "type": "input",
                "key": "preservation_organization_receiver_url"
            },
        ],
        'specification': json.loads(
            open(os.path.join(settings.BASE_DIR, 'templates/eark/EARK_SD_ESSArch.json')).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_submit_description = profile
    sa.save()

    print('Installed profile submit description (EARK)')

    return 0


def installProfileTP(sa):

    dct = {
        'name': 'TP (EARK)',
        'profile_type': 'transfer_project',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Transfer Project profile',
        'template': [
            {
                'key': 'container_format',
                'type': 'select',
                'defaultValue': 'tar',
                'templateOptions': {
                    'label': 'Container format',
                    'options': [
                        {'name': 'TAR', 'value': 'tar'},
                        {'name': 'ZIP', 'value': 'zip'},
                    ]
                }
            },
            {
                "key": "container_format_compression",
                "templateOptions": {
                    "label": "Container format compression",
                    "options": [
                        {
                            "name": "Yes",
                            "value": True
                        },
                        {
                            "name": "No",
                            "value": False
                        }
                    ]
                },
                "defaultValue": False,
                "type": "select"
            },
            {
                'key': 'checksum_algorithm',
                'type': 'select',
                'defaultValue': 'MD5',
                'templateOptions': {
                    'label': 'Checksum algorithm',
                    'options': [
                        {'name': 'MD5', 'value': 'MD5'},
                        {'name': 'SHA-256', 'value': 'SHA-256'},
                    ]
                }
            },
            {
                "templateOptions": {
                    "type": "email",
                    "label": "Preservation organization receiver email",
                },
                "type": "input",
                "key": "preservation_organization_receiver_email"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "remote": "",
                    "label": "Preservation organization receiver url (empty for local)",
                },
                "type": "input",
                "key": "preservation_organization_receiver_url"
            }
        ],
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_transfer_project = profile
    sa.save()

    print('Installed profile transfer project (EARK)')

    return 0


def installProfileAICD(sa):

    dct = {
        'name': 'AIC Description (EARK)',
        'profile_type': 'aic_description',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Archival Information Collection profile',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to Submission Agreement',
        'template': [],
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_AICD_ESSArch.json')
        ).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_aic_description = profile
    sa.save()

    print('Installed profile AIC Description (EARK)')

    return 0


def installProfileAIPD(sa):

    dct = {
        'name': 'AIP Description (EARK)',
        'profile_type': 'aip_description',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Archival Information Package Description profile',
        'representation_info': 'Documentation 1',
        'preservation_descriptive_info': 'Documentation 2',
        'supplemental': 'Documentation 3',
        'access_constraints': 'Documentation 4',
        'datamodel_reference': 'Documentation 5',
        'additional': 'Documentation 6',
        'submission_method': 'Electronically',
        'submission_schedule': 'Once',
        'submission_data_inventory': 'According to Submission Agreement',
        'template': [
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
                "defaultValue": "Creator Organization 1",
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
                    "label": "Archivist Software",
                    "required": True,
                },
                "type": "input",
                "defaultValue": "ESSArch",
                "key": "archivist_software_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Archivist Software Note"
                },
                "type": "input",
                "key": "archivist_software_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Individual",
                },
                "type": "input",
                "defaultValue": "ESSArch",
                "key": "creator_individual_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Individual Note"
                },
                "type": "input",
                "key": "creator_individual_note"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Creator Software",
                },
                "type": "input",
                "defaultValue": "ESSArch",
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
                },
                "type": "input",
                "defaultValue": "ESSArch",
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
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Software",
                },
                "type": "input",
                "defaultValue": "ESSArch",
                "key": "preservation_software_name"
            },
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Preservation Software Note"
                },
                "type": "input",
                "key": "preservation_software_note"
            },
        ],
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_AIPD_ESSArch.json')
        ).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_aip_description = profile
    sa.save()

    print('Installed profile AIP Description (EARK)')

    return 0


def installProfilePM(sa):

    dct = {
        'name': 'PM (EARK)',
        'profile_type': 'preservation_metadata',
        'type': 'Implementation',
        'status': 'Draft',
        'label': 'Preservation Metadata profile',
        'template': [
            {
                "templateOptions": {
                    "type": "text",
                    "label": "Agent Identifier Value"
                },
                "type": "input",
                "defaultValue": "ESSArch",
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
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_PREMIS.json')
        ).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_preservation_metadata = profile
    sa.save()

    print('Installed profile preservation metadata (EARK)')

    return 0


def installProfileWF(sa):

    dct = {
        'name': 'WF (EARK)',
        'profile_type': 'workflow',
        'type': 'workflow',
        'status': 'Draft',
        'label': 'Workflow profile',
        'specification': json.loads(open(
            os.path.join(settings.BASE_DIR, 'templates/eark/EARK_WF_ESSArch.json')
        ).read()),
    }

    profile, _ = Profile.objects.update_or_create(name=dct['name'], defaults=dct)
    sa.profile_workflow = profile
    sa.save()

    print('Installed profile workflow (EARK)')

    return 0


if __name__ == '__main__':
    installProfiles()
