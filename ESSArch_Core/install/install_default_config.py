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

from django.contrib.auth import get_user_model  # noqa
from django.contrib.auth.models import Permission  # noqa
from groups_manager.models import GroupType  # noqa
from elasticsearch.client import IngestClient  # noqa
from elasticsearch_dsl.connections import get_connection  # noqa

from ESSArch_Core.search import alias_migration  # noqa
from ESSArch_Core.auth.models import Group, GroupMemberRole  # noqa
from ESSArch_Core.configuration.models import EventType, Parameter, Path, Site, ArchivePolicy  # noqa
from ESSArch_Core.storage.models import StorageMethod, DISK, StorageTarget, StorageMethodTargetRelation  # noqa
from ESSArch_Core.tags.documents import Archive, Component, Directory, File, InformationPackage  # noqa

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

    print("\nInstalling archive policies...")
    installDefaultArchivePolicies()

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
    dct = {
        'Prepared IP': '10100',
        'Created IP root directory': '10200',
        'Created physical model': '10300',
        'Created SIP': '10400',
        'Submitted SIP': '10500',

        'Delivery received': '20100',
        'Delivery checked': '20200',
        'Delivery registered': '20300',
        'Delivery registered in journal system': '20310',
        'Delivery registered in archival information system': '20320',
        'Delivery receipt sent': '20400',
        'Delivery ready for hand over': '20500',
        'Delivery transferred': '20600',

        'Received the IP for long-term preservation': '30000',
        'Verified IP against archive information system': '30100',
        'Verified IP is approved for long-term preservation': '30110',
        'Created AIP': '30200',
        'Preserved AIP': '30300',
        'Cached AIP': '30310',
        'Removed the source to the SIP': '30400',
        'Removed the source to the AIP': '30410',
        'Ingest order completed': '30500',
        'Ingest order accepted': '30510',
        'Ingest order requested': '30520',
        'Created DIP': '30600',
        'DIP order requested': '30610',
        'DIP order accepted': '30620',
        'DIP order completed': '30630',
        'Moved to workarea': '30700',
        'Moved from workarea': '30710',
        'Moved to gate from workarea': '30720',

        'Unmounted the tape from drive in robot': '40100',
        'Mounted the tape in drive in robot': '40200',
        'Deactivated storage medium': '40300',
        'Quick media verification order requested': '40400',
        'Quick media verification order accepted': '40410',
        'Quick media verification order completed': '40420',
        'Storage medium delivered': '40500',
        'Storage medium received': '40510',
        'Storage medium placed': '40520',
        'Storage medium collected': '40530',
        'Storage medium robot': '40540',
        'Data written to disk storage method': '40600',
        'Data read from disk storage method': '40610',
        'Data written to tape storage method': '40700',
        'Data read from tape storage method': '40710',

        'Calculated checksum ': '50000',
        'Identified format': '50100',
        'Validated file format': '50200',
        'Validated XML file': '50210',
        'Validated logical representation against physical representation': '50220',
        'Validated checksum': '50230',
        'Compared XML files': '50240',
        'Virus control done': '50300',
        'Created TAR': '50400',
        'Created ZIP': '50410',
        'Updated IP status': '50500',
        'Updated IP path': '50510',
        'Generated XML file': '50600',
        'Appended events': '50610',
        'Copied schemas': '50620',
        'Parsed events file': '50630',
        'Uploaded file': '50700',
        'Deleted files': '50710',
        'Unpacked object': '50720',
        'Converted RES to PREMIS': '50730',
        'Deleted IP': '50740',
        'Converted file': '50750',
    }

    for key in dct:
        print('-> %s: %s' % (key, dct[key]))
        EventType.objects.get_or_create(eventType=dct[key], defaults={'eventDetail': key})

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
        'content_location_type': 'SIP',
        #'content_location_type': 'AIP', # TODO: this is moved here from EPP, which collides with above line
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

        # ---- app: configuration ---- model: archivepolicy
        ['add_archivepolicy', 'configuration', 'archivepolicy'],  # Can add archivepolicy
        ['change_archivepolicy', 'configuration', 'archivepolicy'],  # Can change archivepolicy
        ['delete_archivepolicy', 'configuration', 'archivepolicy'],  # Can delete archivepolicy
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
        'path_ingest_reception': '/ESSArch/data/eta/reception/eft',
        'path_ingest_unidentified': '/ESSArch/data/eta/uip',
        'ingest_workarea': '/ESSArch/data/eta/work',
        'reception': '/ESSArch/data/gate/reception',
        'ingest': '/ESSArch/data/epp/ingest',
        'cache': '/ESSArch/data/epp/cache',
        'access_workarea': '/ESSArch/data/epp/work',
        #'ingest_workarea': '/ESSArch/data/epp/work', # TODO: This is copied here from EPP which collides with eta
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


def installDefaultArchivePolicies():
    cache = Path.objects.get(entity='cache')
    ingest = Path.objects.get(entity='ingest')

    ArchivePolicy.objects.get_or_create(
        policy_id='1',
        defaults={
            'checksum_algorithm': ArchivePolicy.MD5,
            'policy_name': 'default',
            'cache_storage': cache, 'ingest_path': ingest,
            'receive_extract_sip': True
        }
    )

    return 0


def installDefaultStorageMethods():
    StorageMethod.objects.get_or_create(
        name='Default Storage Method 1',
        defaults={
            'archive_policy': ArchivePolicy.objects.get(policy_name='default'),
            'status': True,
            'type': DISK,
            'containers': False,
        }
    )

    StorageMethod.objects.get_or_create(
        name='Default Long-term Storage Method 1',
        defaults={
            'archive_policy': ArchivePolicy.objects.get(policy_name='default'),
            'status': True,
            'type': DISK,
            'containers': True,
        }
    )

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
        defaults={
            'status': True,
            'storage_method': StorageMethod.objects.get(name='Default Storage Method 1'),
            'storage_target': StorageTarget.objects.get(name='Default Storage Target 1'),
        }
    )

    StorageMethodTargetRelation.objects.get_or_create(
        name='Default Long-term Storage Method Target Relation 1',
        defaults={
            'status': True,
            'storage_method': StorageMethod.objects.get(name='Default Long-term Storage Method 1'),
            'storage_target': StorageTarget.objects.get(name='Default Long-term Storage Target 1'),
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
