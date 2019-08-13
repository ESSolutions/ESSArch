# -*- coding: UTF-8 -*-

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

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa isort:skip
from django.contrib.auth.models import Permission  # noqa isort:skip
from groups_manager.models import GroupType  # noqa isort:skip
from elasticsearch.client import IngestClient  # noqa isort:skip
from elasticsearch_dsl.connections import get_connection  # noqa isort:skip

from ESSArch_Core.search import alias_migration  # noqa isort:skip
from ESSArch_Core.auth.models import Group, GroupMemberRole  # noqa isort:skip
from ESSArch_Core.configuration.models import EventType, Parameter, Path, Site, StoragePolicy  # noqa isort:skip
from ESSArch_Core.storage.models import StorageMethod, DISK, StorageTarget, StorageMethodTargetRelation  # noqa isort:skip
from ESSArch_Core.tags.documents import Archive, Component, Directory, File, InformationPackage  # noqa isort:skip

User = get_user_model()


def installDefaultConfiguration():
    print("Installing event types...")
    installDefaultEventTypes()

    print("Installing parameters...")
    installDefaultParameters()

    print("Installing site...")
    installDefaultSite()

    print("Installing users, groups and permissions...")
    installDefaultUsers()

    print("\nInstalling paths...")
    installDefaultPaths()

    print("\nInstalling storage policies...")
    installDefaultStoragePolicies()

    print("\nInstalling storage methods...")
    installDefaultStorageMethods()

    print("\nInstalling storage targets...")
    installDefaultStorageTargets()

    print("\nInstalling storage method target relations...")
    installDefaultStorageMethodTargetRelations()

    print("\nInstalling Elasticsearch pipelines...")
    installPipelines()

    print("\nInstalling search indices...")
    installSearchIndices()

    return 0


def installDefaultEventTypes():
    ip_cat = EventType.CATEGORY_INFORMATION_PACKAGE
    delivery_cat = EventType.CATEGORY_DELIVERY

    dct = {
        'Prepared IP': {'eventType': '10100', 'category': ip_cat},
        'Created IP root directory': {'eventType': '10200', 'category': ip_cat},
        'Created physical model': {'eventType': '10300', 'category': ip_cat},
        'Created SIP': {'eventType': '10400', 'category': ip_cat},
        'Submitted SIP': {'eventType': '10500', 'category': ip_cat},

        'Delivery received': {'eventType': '20100', 'category': delivery_cat},
        'Delivery checked': {'eventType': '20200', 'category': delivery_cat},
        'Delivery registered': {'eventType': '20300', 'category': delivery_cat},
        'Delivery registered in journal system': {'eventType': '20310', 'category': delivery_cat},
        'Delivery registered in archival information system': {'eventType': '20320', 'category': delivery_cat},
        'Delivery receipt sent': {'eventType': '20400', 'category': delivery_cat},
        'Delivery ready for hand over': {'eventType': '20500', 'category': delivery_cat},
        'Delivery transferred': {'eventType': '20600', 'category': delivery_cat},
        'Delivery approved': {'eventType': '20700', 'category': delivery_cat},
        'Delivery rejected': {'eventType': '20800', 'category': delivery_cat},

        'Received the IP for long-term preservation': {'eventType': '30000', 'category': ip_cat},
        'Verified IP against archive information system': {'eventType': '30100', 'category': ip_cat},
        'Verified IP is approved for long-term preservation': {'eventType': '30110', 'category': ip_cat},
        'Created AIP': {'eventType': '30200', 'category': ip_cat},
        'Preserved AIP': {'eventType': '30300', 'category': ip_cat},
        'Cached AIP': {'eventType': '30310', 'category': ip_cat},
        'Removed the source to the SIP': {'eventType': '30400', 'category': ip_cat},
        'Removed the source to the AIP': {'eventType': '30410', 'category': ip_cat},
        'Ingest order completed': {'eventType': '30500', 'category': ip_cat},
        'Ingest order accepted': {'eventType': '30510', 'category': ip_cat},
        'Ingest order requested': {'eventType': '30520', 'category': ip_cat},
        'Created DIP': {'eventType': '30600', 'category': ip_cat},
        'DIP order requested': {'eventType': '30610', 'category': ip_cat},
        'DIP order accepted': {'eventType': '30620', 'category': ip_cat},
        'DIP order completed': {'eventType': '30630', 'category': ip_cat},
        'Moved to workarea': {'eventType': '30700', 'category': ip_cat},
        'Moved from workarea': {'eventType': '30710', 'category': ip_cat},
        'Moved to gate from workarea': {'eventType': '30720', 'category': ip_cat},

        'Unmounted the tape from drive in robot': {'eventType': '40100', 'category': ip_cat},
        'Mounted the tape in drive in robot': {'eventType': '40200', 'category': ip_cat},
        'Deactivated storage medium': {'eventType': '40300', 'category': ip_cat},
        'Quick media verification order requested': {'eventType': '40400', 'category': ip_cat},
        'Quick media verification order accepted': {'eventType': '40410', 'category': ip_cat},
        'Quick media verification order completed': {'eventType': '40420', 'category': ip_cat},
        'Storage medium delivered': {'eventType': '40500', 'category': ip_cat},
        'Storage medium received': {'eventType': '40510', 'category': ip_cat},
        'Storage medium placed': {'eventType': '40520', 'category': ip_cat},
        'Storage medium collected': {'eventType': '40530', 'category': ip_cat},
        'Storage medium robot': {'eventType': '40540', 'category': ip_cat},
        'Data written to disk storage method': {'eventType': '40600', 'category': ip_cat},
        'Data read from disk storage method': {'eventType': '40610', 'category': ip_cat},
        'Data written to tape storage method': {'eventType': '40700', 'category': ip_cat},
        'Data read from tape storage method': {'eventType': '40710', 'category': ip_cat},

        'Calculated checksum ': {'eventType': '50000', 'category': ip_cat},
        'Identified format': {'eventType': '50100', 'category': ip_cat},
        'Validated file format': {'eventType': '50200', 'category': ip_cat},
        'Validated XML file': {'eventType': '50210', 'category': ip_cat},
        'Validated logical representation against physical representation': {'eventType': '50220', 'category': ip_cat},
        'Validated checksum': {'eventType': '50230', 'category': ip_cat},
        'Compared XML files': {'eventType': '50240', 'category': ip_cat},
        'Virus control done': {'eventType': '50300', 'category': ip_cat},
        'Created TAR': {'eventType': '50400', 'category': ip_cat},
        'Created ZIP': {'eventType': '50410', 'category': ip_cat},
        'Updated IP status': {'eventType': '50500', 'category': ip_cat},
        'Updated IP path': {'eventType': '50510', 'category': ip_cat},
        'Generated XML file': {'eventType': '50600', 'category': ip_cat},
        'Appended events': {'eventType': '50610', 'category': ip_cat},
        'Copied schemas': {'eventType': '50620', 'category': ip_cat},
        'Parsed events file': {'eventType': '50630', 'category': ip_cat},
        'Uploaded file': {'eventType': '50700', 'category': ip_cat},
        'Deleted files': {'eventType': '50710', 'category': ip_cat},
        'Unpacked object': {'eventType': '50720', 'category': ip_cat},
        'Converted RES to PREMIS': {'eventType': '50730', 'category': ip_cat},
        'Deleted IP': {'eventType': '50740', 'category': ip_cat},
        'Converted file': {'eventType': '50750', 'category': ip_cat},
    }

    for key, val in dct.items():
        print('-> %s: %s' % (key, val['eventType']))
        EventType.objects.update_or_create(
            eventType=val['eventType'],
            defaults={
                'eventDetail': key,
                'category': val['category'],
            },
        )

    return 0


def installDefaultParameters():
    site_name = 'Site-X'
    dct = {
        'agent_identifier_type': 'ESS',
        'agent_identifier_value': 'ESS',
        'event_identifier_type': 'ESS',
        'linking_agent_identifier_type': 'ESS',
        'linking_object_identifier_type': 'ESS',
        'object_identifier_type': 'ESS',
        'related_object_identifier_type': 'ESS',
        'site_name': site_name,
        'medium_location': 'Media_%s' % site_name,
    }

    for key in dct:
        print('-> %s: %s' % (key, dct[key]))
        Parameter.objects.get_or_create(entity=key, defaults={'value': dct[key]})

    return 0


def installDefaultSite():
    Site.objects.get_or_create(name='ESSArch')


def installDefaultUsers():

    #####################################
    # Groups and permissions
    organization, _ = GroupType.objects.get_or_create(label="organization")
    default_org, _ = Group.objects.get_or_create(name='Default', group_type=organization)

    role_user, _ = GroupMemberRole.objects.get_or_create(codename='user')
    permission_list_user = [
        # ---- app: ip ---- model: informationpackage
        ['view_informationpackage', 'ip', 'informationpackage'],       # Can view information packages
        ['add_informationpackage', 'ip', 'informationpackage'],        # Can add Information Package
        ['delete_informationpackage', 'ip', 'informationpackage'],     # Can delete Information Package (Ingest)
        ['can_upload', 'ip', 'informationpackage'],                    # Can upload files to IP
        ['set_uploaded', 'ip', 'informationpackage'],                  # Can set IP as uploaded
        ['create_sip', 'ip', 'informationpackage'],                    # Can create SIP
        ['submit_sip', 'ip', 'informationpackage'],                    # Can submit SIP
        ['prepare_ip', 'ip', 'informationpackage'],                    # Can prepare IP
        ['receive', 'ip', 'informationpackage'],                       # Can receive IP
        ['preserve', 'ip', 'informationpackage'],                      # Can preserve IP (Ingest)
        ['preserve_dip', 'ip', 'informationpackage'],                  # Can preserve DIP (Access)
        ['get_from_storage', 'ip', 'informationpackage'],              # Can get extracted IP from storage (Access)
        ['get_tar_from_storage', 'ip', 'informationpackage'],          # Can get packaged IP from storage (Access)
        ['add_to_ingest_workarea', 'ip', 'informationpackage'],        # Can add IP to ingest workarea "readonly" (Ing)
        ['diff-check', 'ip', 'informationpackage'],                    # Can diff-check IP (?)
        # ---- app: ip ---- model: workarea
        ['move_from_ingest_workarea', 'ip', 'workarea'],               # Can move IP from ingest workarea (Ingest)
        ['move_from_access_workarea', 'ip', 'workarea'],               # Can move IP from access workarea (Access)
        ['preserve_from_ingest_workarea', 'ip', 'workarea'],           # Can preserve IP from ingest workarea (Ingest)
        ['preserve_from_access_workarea', 'ip', 'workarea'],           # Can preserve IP from access workarea (Access)
        # ---- app: ip ---- model: order
        ['prepare_order', 'ip', 'order'],                              # Can prepare order (Access)
        # ---- app: WorkflowEngine ---- model: processtask
        # ['can_undo','WorkflowEngine','processtask'],                 # Can undo tasks (other)
        # ['can_retry','WorkflowEngine','processtask'],                # Can retry tasks (other)
        # ---- app: tags ---- model: Tag
        ['search', 'tags', 'tag'],  # Can search
        ['transfer_sip', 'ip', 'informationpackage'],                  # Can transfer SIP
        # ---- app: WorkflowEngine ---- model: processtask
        # ['can_undo','WorkflowEngine','processtask'],                 # Can undo tasks (other)
        # ['can_retry','WorkflowEngine','processtask'],                # Can retry tasks (other)
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_user.permissions.add(p_obj)

    role_admin, _ = GroupMemberRole.objects.get_or_create(codename='admin')
    permission_list_admin = [
        # ---- app: profiles ---- model: submissionagreement
        ['add_submissionagreement', 'profiles', 'submissionagreement'],  # Can add Submission Agreement (Import)
        ['change_submissionagreement', 'profiles', 'submissionagreement'],  # Can change Submission Agreement
        # ---- app: profiles ---- model: profile
        ['add_profile', 'profiles', 'profile'],  # Can add Profile (Import/Administration)
        ['change_profile', 'profiles', 'profile'],  # Can change Profile
        # ---- app: WorkflowEngine ---- model: processtask
        # ['can_undo','WorkflowEngine','processtask'],             # Can undo tasks (other)
        # ['can_retry','WorkflowEngine','processtask'],             # Can retry tasks (other)
        # ---- app: ip ---- model: informationpackage
        ['get_from_storage_as_new', 'ip', 'informationpackage'],  # Can get IP "as new" from storage (Access)
        ['add_to_ingest_workarea_as_new', 'ip', 'informationpackage'],
        # Can add IP as new generation to ingest workarea (Ingest)
        # ---- app: ip ---- model: order
        ['prepare_order', 'ip', 'order'],  # Can prepare order (Access)
        # ---- app: storage ---- model: storageobject
        ['storage_migration', 'storage', 'storageobject'],  # Storage migration (Administration)
        ['storage_maintenance', 'storage', 'storageobject'],  # Storage maintenance (Administration)
        ['storage_management', 'storage', 'storageobject'],  # Storage management (Administration)
        # ---- app: maintenance ---- model: AppraisalRule
        ['add_appraisalrule', 'maintenance', 'appraisalrule'],  # Can add appraisal rule (Administration)
        # ---- app: maintenance ---- model: ConversionRule
        ['add_conversionrule', 'maintenance', 'conversionrule'],  # Can add conversion rule (Administration)
        # ---- app: tags ---- model: Tag
        ['create_archive', 'tags', 'tag'],  # Can create archives
    ]

    for p in permission_list_admin:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_admin.permissions.add(p_obj)

    role_sysadmin, _ = GroupMemberRole.objects.get_or_create(codename='sysadmin')
    permission_list_sysadmin = [
        # ---- app: auth ---- model: group
        ['add_group', 'auth', 'group'],                    # Can add group
        ['change_group', 'auth', 'group'],                    # Can change group
        ['delete_group', 'auth', 'group'],                    # Can delete group
        # ---- app: auth ---- model: user
        ['add_user', 'auth', 'user'],                    # Can add user
        ['change_user', 'auth', 'user'],                    # Can change user
        ['delete_user', 'auth', 'user'],                    # Can delete user
        # ---- app: configuration ---- model: parameter
        ['add_parameter', 'configuration', 'parameter'],                    # Can add parameter
        ['change_parameter', 'configuration', 'parameter'],                    # Can change parameter
        ['delete_parameter', 'configuration', 'parameter'],                    # Can delete parameter
        # ---- app: configuration ---- model: path
        ['add_path', 'configuration', 'path'],                    # Can add path
        ['change_path', 'configuration', 'path'],                    # Can change path
        ['delete_path', 'configuration', 'path'],                    # Can delete path
        # ---- app: configuration ---- model: eventtype
        ['add_eventtype', 'configuration', 'eventtype'],                    # Can add eventtype
        ['change_eventtype', 'configuration', 'eventtype'],                    # Can change eventtype
        ['delete_eventtype', 'configuration', 'eventtype'],                    # Can delete eventtype
        # ---- app: profiles ---- model: profile
        ['add_profile', 'profiles', 'profile'],                    # Can add profile
        ['change_profile', 'profiles', 'profile'],                    # Can change profile
        ['delete_profile', 'profiles', 'profile'],                    # Can delete profile
        # ---- app: profiles ---- model: submissionagreement
        ['add_submissionagreement', 'profiles', 'submissionagreement'],     # Can add submissionagreement
        ['change_submissionagreement', 'profiles', 'submissionagreement'],  # Can change submissionagreement
        ['delete_submissionagreement', 'profiles', 'submissionagreement'],  # Can delete submissionagreement
        # ---- app: groups_manager ---- model: grouptype
        ['add_grouptype', 'groups_manager', 'grouptype'],                    # Can add grouptype
        ['change_grouptype', 'groups_manager', 'grouptype'],                    # Can change grouptype
        ['delete_grouptype', 'groups_manager', 'grouptype'],                    # Can delete grouptype

        # ---- app: configuration ---- model: storagepolicy
        ['add_storagepolicy', 'configuration', 'storagepolicy'],  # Can add storagepolicy
        ['change_storagepolicy', 'configuration', 'storagepolicy'],  # Can change storagepolicy
        ['delete_storagepolicy', 'configuration', 'storagepolicy'],  # Can delete storagepolicy
        # ---- app: storage ---- model: storagemethod
        ['add_storagemethod', 'storage', 'storagemethod'],  # Can add storagemethod
        ['change_storagemethod', 'storage', 'storagemethod'],  # Can change storagemethod
        ['delete_storagemethod', 'storage', 'storagemethod'],  # Can delete storagemethod
        # ---- app: storage ---- model: storagetarget
        ['add_storagetarget', 'storage', 'storagetarget'],  # Can add storagetarget
        ['change_storagetarget', 'storage', 'storagetarget'],  # Can change storagetarget
        ['delete_storagetarget', 'storage', 'storagetarget'],  # Can delete storagetarget
        # ---- app: storage ---- model: storagemethodtargetrelation
        [
            'add_storagemethodtargetrelation', 'storage',
            'storagemethodtargetrelation'
        ],  # Can add storagemethodtargetrelation
        [
            'change_storagemethodtargetrelation', 'storage',
            'storagemethodtargetrelation'
        ],  # Can change storagemethodtargetrelation

        [
            'delete_storagemethodtargetrelation', 'storage',
            'storagemethodtargetrelation'
        ],  # Can delete storagemethodtargetrelation

        # ---- app: storage ---- model: storageobject
        ['storage_migration', 'storage', 'storageobject'],  # Storage migration (Administration)
        ['storage_maintenance', 'storage', 'storageobject'],  # Storage maintenance (Administration)
        ['storage_management', 'storage', 'storageobject'],  # Storage management (Administration)
        # ---- app: storage ---- model: ioqueue
        ['change_ioqueue', 'storage', 'ioqueue'],  # Can change ioqueue
        ['delete_ioqueue', 'storage', 'ioqueue'],  # Can delete ioqueue
        # ---- app: storage ---- model: robot
        ['add_robot', 'storage', 'robot'],  # Can add robot
        ['change_robot', 'storage', 'robot'],  # Can change robot
        ['delete_robot', 'storage', 'robot'],  # Can delete robot
        # ---- app: storage ---- model: robotqueue
        ['change_robotqueue', 'storage', 'robotqueue'],  # Can change robotqueue
        ['delete_robotqueue', 'storage', 'robotqueue'],  # Can delete robotqueue
        # ---- app: storage ---- model: tapedrive
        ['add_tapedrive', 'storage', 'tapedrive'],  # Can add tapedrive
        ['change_tapedrive', 'storage', 'tapedrive'],  # Can change tapedrive
        ['delete_tapedrive', 'storage', 'tapedrive'],  # Can delete tapedrive
    ]

    for p in permission_list_sysadmin:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_sysadmin.permissions.add(p_obj)

    #####################################
    # Users
    user_superuser, created = User.objects.get_or_create(
        first_name='superuser', last_name='Lastname',
        username='superuser', email='superuser@essolutions.se',
    )
    if created:
        user_superuser.set_password('superuser')
        user_superuser.is_staff = True
        user_superuser.is_superuser = True
        user_superuser.save()
        default_org.add_member(user_superuser.essauth_member)

    user_user, created = User.objects.get_or_create(
        first_name='user', last_name='Lastname',
        username='user', email='user@essolutions.se'
    )
    if created:
        user_user.set_password('user')
        user_user.save()
        default_org.add_member(user_user.essauth_member, roles=[role_user])

    user_admin, created = User.objects.get_or_create(
        first_name='admin', last_name='Lastname',
        username='admin', email='admin@essolutions.se',
    )
    if created:
        user_admin.set_password('admin')
        user_admin.is_staff = True
        user_admin.save()
        default_org.add_member(user_admin.essauth_member, roles=[role_user, role_admin])

    user_sysadmin, created = User.objects.get_or_create(
        first_name='sysadmin', last_name='Lastname',
        username='sysadmin', email='sysadmin@essolutions.se',
    )
    if created:
        user_sysadmin.set_password('sysadmin')
        user_sysadmin.is_staff = True
        user_sysadmin.save()
        default_org.add_member(user_sysadmin.essauth_member, roles=[role_sysadmin])

    return 0


def installDefaultPaths():
    dct = {
        'path_mimetypes_definitionfile': '/ESSArch/config/mime.types',
        'path_definitions': '/ESSArch/etp/env',
        'path_gate_reception': '/ESSArch/data/gate/reception',
        'path_preingest_prepare': '/ESSArch/data/etp/prepare',
        'path_preingest_reception': '/ESSArch/data/etp/reception',
        'path_ingest_reception': '/ESSArch/data/gate/reception',
        'path_ingest_unidentified': '/ESSArch/data/eta/uip',
        'reception': '/ESSArch/data/gate/reception',
        'ingest': '/ESSArch/data/epp/ingest',
        'access_workarea': '/ESSArch/data/epp/work',
        'ingest_workarea': '/ESSArch/data/epp/work',
        'disseminations': '/ESSArch/data/epp/disseminations',
        'orders': '/ESSArch/data/epp/orders',
        'verify': '/ESSArch/data/epp/verify',
        'temp': '/ESSArch/data/epp/temp',
        'appraisal_reports': '/ESSArch/data/epp/reports/appraisal',
        'conversion_reports': '/ESSArch/data/epp/reports/conversion',
    }

    for key in dct:
        print('-> %s: %s' % (key, dct[key]))
        Path.objects.get_or_create(entity=key, defaults={'value': dct[key]})

    return 0


def installDefaultStoragePolicies():
    cache_method, created_cache_method = StorageMethod.objects.get_or_create(
        name='Default Cache Storage Method',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': False,
        }
    )

    if created_cache_method:
        cache_target = StorageTarget.objects.create(
            name='Default Cache Storage Target 1',
            status=True,
            type=DISK,
            target='/ESSArch/data/store/cache',
        )

        StorageMethodTargetRelation.objects.create(
            name='Default Cache Storage Method Target Relation 1',
            status=True,
            storage_method=cache_method,
            storage_target=cache_target,
        )

    ingest = Path.objects.get(entity='ingest')

    policy, created_policy = StoragePolicy.objects.get_or_create(
        policy_id='1',
        defaults={
            'checksum_algorithm': StoragePolicy.MD5,
            'policy_name': 'default',
            'cache_storage': cache_method, 'ingest_path': ingest,
            'receive_extract_sip': True,
            'cache_minimum_capacity': 0,
            'cache_maximum_age': 0,
        }
    )

    if created_policy or created_cache_method:
        policy.storage_methods.add(cache_method)

    return 0


def installDefaultStorageMethods():
    sm1, _ = StorageMethod.objects.get_or_create(
        name='Default Storage Method 1',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': False,
        }
    )

    sm2, _ = StorageMethod.objects.get_or_create(
        name='Default Long-term Storage Method 1',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': True,
        }
    )

    default_policy = StoragePolicy.objects.get(policy_name='default')
    default_policy.storage_methods.add(sm1, sm2)

    return 0


def installDefaultStorageTargets():
    StorageTarget.objects.get_or_create(
        name='Default Storage Target 1',
        defaults={
            'status': True,
            'type': DISK,
            'target': '/ESSArch/data/store/disk1',
        }
    )

    StorageTarget.objects.get_or_create(
        name='Default Long-term Storage Target 1',
        defaults={
            'status': True,
            'type': DISK,
            'target': '/ESSArch/data/store/longterm_disk1',
        }
    )

    return 0


def installDefaultStorageMethodTargetRelations():
    StorageMethodTargetRelation.objects.get_or_create(
        name='Default Storage Method Target Relation 1',
        storage_method=StorageMethod.objects.get(name='Default Storage Method 1'),
        storage_target=StorageTarget.objects.get(name='Default Storage Target 1'),
        defaults={
            'status': True,
        }
    )

    StorageMethodTargetRelation.objects.get_or_create(
        name='Default Long-term Storage Method Target Relation 1',
        storage_method=StorageMethod.objects.get(name='Default Long-term Storage Method 1'),
        storage_target=StorageTarget.objects.get(name='Default Long-term Storage Target 1'),
        defaults={
            'status': True,
        }
    )

    return 0


def installPipelines():
    conn = get_connection()
    client = IngestClient(conn)
    client.put_pipeline(id='ingest_attachment', body={
        'description': "Extract attachment information",
        'processors': [
            {
                "attachment": {
                    "field": "data"
                },
                "remove": {
                    "field": "data"
                }
            }
        ]
    })
    client.put_pipeline(id='add_timestamp', body={
        'description': "Adds an index_date timestamp",
        'processors': [
            {
                "set": {
                    "field": "index_date",
                    "value": "{{_ingest.timestamp}}",
                },
            },
        ]
    })


def installSearchIndices():
    for doctype in [Archive, Component, Directory, File, InformationPackage]:
        alias_migration.setup_index(doctype)

    print('done')


if __name__ == '__main__':
    installDefaultConfiguration()
