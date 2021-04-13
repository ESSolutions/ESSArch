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
import click
import django

django.setup()

from pydoc import locate  # noqa isort:skip

from django.conf import settings  # noqa isort:skip
from django.contrib.auth import get_user_model  # noqa isort:skip
from django.contrib.auth.models import Permission  # noqa isort:skip
from groups_manager.models import GroupType  # noqa isort:skip
from elasticsearch.client import IngestClient  # noqa isort:skip
from elasticsearch_dsl.connections import get_connection  # noqa isort:skip

from ESSArch_Core.search import alias_migration  # noqa isort:skip
from ESSArch_Core.auth.models import Group, GroupMemberRole  # noqa isort:skip
from ESSArch_Core.configuration.models import EventType, Feature, Parameter, Path, Site, StoragePolicy  # noqa isort:skip
from ESSArch_Core.storage.models import (  # noqa isort:skip
    DISK,
    StorageMedium,
    StorageMethod,
    StorageMethodTargetRelation,
    StorageTarget,
)

User = get_user_model()


def installDefaultConfiguration():

    installDefaultFeatures()
    installDefaultEventTypes()
    installDefaultParameters()
    installDefaultSite()
    installDefaultUsers()
    installDefaultPaths()
    installDefaultStoragePolicies()
    installDefaultStorageMethods()
    installDefaultStorageTargets()
    installDefaultStorageMethodTargetRelations()
    installPipelines()
    installSearchIndices()

    return 0


def installDefaultFeatures():
    click.echo('Installing default features:')

    features = [
        {
            'name': 'archival descriptions',
            'enabled': True,
        },
        {
            'name': 'receive',
            'enabled': True,
        },
        {
            'name': 'transfer',
            'enabled': False,
        },
    ]

    for feature in features:
        click.secho('- {}... '.format(feature['name']), nl=False)
        f, _ = Feature.objects.get_or_create(
            name=feature['name'],
            defaults={
                'enabled': feature['enabled'],
                'description': feature.get('description', ''),
            }
        )
        click.secho('enabled' if f.enabled else 'disabled', fg='green' if f.enabled else 'red')

    return


def installDefaultEventTypes():
    click.echo("Installing event types...")

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
        'Conversion': {'eventType': '50750', 'category': ip_cat},
        'Action tool': {'eventType': '50760', 'category': ip_cat},
    }

    for key, val in dct.items():
        print('-> %s: %s' % (key, val['eventType']))
        EventType.objects.get_or_create(
            eventType=val['eventType'],
            defaults={
                'eventDetail': key,
                'category': val['category'],
            },
        )

    return 0


def installDefaultParameters():
    click.echo("Installing parameters...")

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
    click.echo("Installing site...")

    Site.objects.get_or_create(name='ESSArch')


def installDefaultUsers():
    click.echo("Installing users, roles and permissions...")

    organization, _ = GroupType.objects.get_or_create(label="organization")
    default_org, _ = Group.objects.get_or_create(name='Default', group_type=organization)

    #####################################
    # Roles and permissions
    # click.echo('Installing Roles ...')

    role_user, _ = GroupMemberRole.objects.get_or_create(codename='User')
    permission_list_user = [
        ['view_informationpackage', 'ip', 'informationpackage'],  # Can view information package
        ['can_upload', 'ip', 'informationpackage'],  # Can upload files to IP
        ['set_uploaded', 'ip', 'informationpackage'],  # Can set IP as uploaded
        ['create_sip', 'ip', 'informationpackage'],  # Can create SIP
        ['submit_sip', 'ip', 'informationpackage'],  # Can submit SIP
        ['prepare_ip', 'ip', 'informationpackage'],  # Can prepare IP
        ['view_workarea', 'ip', 'workarea'],  # Can view workarea
        ['view_order', 'ip', 'order'],  # Can view order
        ['view_ordertype', 'ip', 'ordertype'],  # Can view order type
        ['view_submissionagreement', 'profiles', 'submissionagreement'],  # Can view submission agreement
        ['view_profile', 'profiles', 'profile'],  # Can view profile
        ['view_profileip', 'profiles', 'profileip'],  # Can view profile ip
        ['view_submissionagreementipdata', 'profiles',
            'submissionagreementipdata'],  # Can view submission agreement ip data
        ['view_appraisaljob', 'maintenance', 'appraisaljob'],  # Can view appraisal job
        ['view_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can view appraisal job entry
        ['view_conversionjob', 'maintenance', 'conversionjob'],  # Can view conversion job
        ['view_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can view conversion job entry
        ['view_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can view appraisal template
        ['view_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can view conversion template
        ['view_tag', 'tags', 'tag'],  # Can view tag
        ['search', 'tags', 'tag'],  # Can search
        ['view_structure', 'tags', 'structure'],  # Can view structure
        ['view_tagstructure', 'tags', 'tagstructure'],  # Can view tag structure
        ['view_tagversion', 'tags', 'tagversion'],  # Can view tag version
        ['view_structureunit', 'tags', 'structureunit'],  # Can view structure unit
        ['view_mediumtype', 'tags', 'mediumtype'],  # Can view medium type
        ['view_nodeidentifier', 'tags', 'nodeidentifier'],  # Can view node identifier
        ['view_nodeidentifiertype', 'tags', 'nodeidentifiertype'],  # Can view node identifier type
        ['view_nodenote', 'tags', 'nodenote'],  # Can view node note
        ['view_nodenotetype', 'tags', 'nodenotetype'],  # Can view node note type
        ['view_noderelationtype', 'tags', 'noderelationtype'],  # Can view node relation type
        ['view_ruleconventiontype', 'tags', 'ruleconventiontype'],  # Can view rule convention type
        ['view_structuretype', 'tags', 'structuretype'],  # Can view structure type
        ['view_structureunitrelation', 'tags', 'structureunitrelation'],  # Can view structure unit relation
        ['view_structureunittype', 'tags', 'structureunittype'],  # Can view structure unit type
        ['view_tagversionrelation', 'tags', 'tagversionrelation'],  # Can view tag version relation
        ['view_search', 'tags', 'search'],  # Can view search
        ['view_tagversiontype', 'tags', 'tagversiontype'],  # Can view node type
        ['view_location', 'tags', 'location'],  # Can view location
        ['view_locationfunctiontype', 'tags', 'locationfunctiontype'],  # Can view location function type
        ['view_locationleveltype', 'tags', 'locationleveltype'],  # Can view location level type
        ['view_metrictype', 'tags', 'metrictype'],  # Can view metric type
        ['view_delivery', 'tags', 'delivery'],  # Can view delivery
        ['view_deliverytype', 'tags', 'deliverytype'],  # Can view delivery type
        ['view_transfer', 'tags', 'transfer'],  # Can view transfer
        ['view_structurerelationtype', 'tags', 'structurerelationtype'],  # Can view structure relation type
        ['view_structurerelation', 'tags', 'structurerelation'],  # Can view structure relation
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_user.permissions.add(p_obj)

    role_producer, _ = GroupMemberRole.objects.get_or_create(codename='Producer')
    permission_list_user = [
        ['add_informationpackage', 'ip', 'informationpackage'],  # Can add information package
        ['delete_informationpackage', 'ip', 'informationpackage'],  # Can delete information package
        ['view_informationpackage', 'ip', 'informationpackage'],  # Can view information package
        ['can_upload', 'ip', 'informationpackage'],  # Can upload files to IP
        ['create_sip', 'ip', 'informationpackage'],  # Can create SIP
        ['submit_sip', 'ip', 'informationpackage'],  # Can submit SIP
        ['prepare_ip', 'ip', 'informationpackage'],  # Can prepare IP
        ['see_other_user_ip_files', 'ip', 'informationpackage'],  # Can see files in other users IPs
        ['add_eventip', 'ip', 'eventip'],  # Can add Events related to IP
        ['change_profileip', 'profiles', 'profileip'],  # Can change profile ip
        ['add_profileipdata', 'profiles', 'profileipdata'],  # Can add profile ip data
        ['add_submissionagreementipdata', 'profiles',
            'submissionagreementipdata'],  # Can add submission agreement ip data
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_producer.permissions.add(p_obj)

    try:
        role_submitter = GroupMemberRole.objects.get(codename='Submitter')
        click.secho("-> role 'Submitter' already exist", fg='red')
    except GroupMemberRole.DoesNotExist:
        click.echo("-> installing role 'Submitter'")
        role_submitter, _ = GroupMemberRole.objects.get_or_create(codename='Submitter')
        permission_list_user = [
            ['view_informationpackage', 'ip', 'informationpackage'],  # Can view information package
            ['submit_sip', 'ip', 'informationpackage'],  # Can submit SIP
            ['see_other_user_ip_files', 'ip', 'informationpackage'],  # Can see files in other users IPs
            ['add_eventip', 'ip', 'eventip'],  # Can add Events related to IP
        ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_submitter.permissions.add(p_obj)

    role_delivery_manager, _ = GroupMemberRole.objects.get_or_create(codename='Delivery Manager')
    permission_list_user = [
        ['add_informationpackage', 'ip', 'informationpackage'],  # Can add information package
        ['delete_informationpackage', 'ip', 'informationpackage'],  # Can delete information package
        ['view_informationpackage', 'ip', 'informationpackage'],  # Can view information package
        ['can_upload', 'ip', 'informationpackage'],  # Can upload files to IP
        ['create_sip', 'ip', 'informationpackage'],  # Can create SIP
        ['submit_sip', 'ip', 'informationpackage'],  # Can submit SIP
        ['transfer_sip', 'ip', 'informationpackage'],  # Can transfer SIP
        ['change_sa', 'ip', 'informationpackage'],  # Can change SA connected to IP
        ['lock_sa', 'ip', 'informationpackage'],  # Can lock SA to IP
        ['receive', 'ip', 'informationpackage'],  # Can receive IP
        ['preserve', 'ip', 'informationpackage'],  # Can preserve IP
        ['add_to_ingest_workarea', 'ip', 'informationpackage'],  # Can add IP to ingest workarea
        ['add_to_ingest_workarea_as_tar', 'ip', 'informationpackage'],  # Can add IP as tar to ingest workarea
        ['add_to_ingest_workarea_as_new', 'ip',
            'informationpackage'],  # Can add IP as new generation to ingest workarea
        ['prepare_ip', 'ip', 'informationpackage'],  # Can prepare IP
        ['delete_first_generation', 'ip', 'informationpackage'],  # Can delete first generation of IP
        ['delete_last_generation', 'ip', 'informationpackage'],  # Can delete last generation of IP
        ['see_other_user_ip_files', 'ip', 'informationpackage'],  # Can see files in other users IPs
        ['add_eventip', 'ip', 'eventip'],  # Can add Events related to IP
        ['change_profileip', 'profiles', 'profileip'],  # Can change profile ip
        ['add_profileipdata', 'profiles', 'profileipdata'],  # Can add profile ip data
        ['add_submissionagreementipdata', 'profiles',
            'submissionagreementipdata'],  # Can add submission agreement ip data
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_delivery_manager.permissions.add(p_obj)

    role_archivist, _ = GroupMemberRole.objects.get_or_create(codename='Archivist')
    permission_list_user = [
        ['view_agent', 'agents', 'agent'],  # Can view agent
        ['view_agentfunction', 'agents', 'agentfunction'],  # Can view agent function
        ['view_agentidentifier', 'agents', 'agentidentifier'],  # Can view agent identifier
        ['view_agentidentifiertype', 'agents', 'agentidentifiertype'],  # Can view agent identifier type
        ['view_agentname', 'agents', 'agentname'],  # Can view agent name
        ['view_agentnametype', 'agents', 'agentnametype'],  # Can view agent name type
        ['view_agentnote', 'agents', 'agentnote'],  # Can view agent note
        ['view_agentnotetype', 'agents', 'agentnotetype'],  # Can view agent note type
        ['view_agentplace', 'agents', 'agentplace'],  # Can view agent place
        ['view_agentplacetype', 'agents', 'agentplacetype'],  # Can view agent place type
        ['view_agentrelation', 'agents', 'agentrelation'],  # Can view agent relation
        ['view_agentrelationtype', 'agents', 'agentrelationtype'],  # Can view agent relation type
        ['view_agenttaglink', 'agents', 'agenttaglink'],  # Can view Agent node relation
        ['view_agenttaglinkrelationtype', 'agents', 'agenttaglinkrelationtype'],  # Can view agent tag relation type
        ['view_agenttype', 'agents', 'agenttype'],  # Can view agent type
        ['view_authoritytype', 'agents', 'authoritytype'],  # Can view authority type
        ['view_mainagenttype', 'agents', 'mainagenttype'],  # Can view main agent type
        ['view_refcode', 'agents', 'refcode'],  # Can view ref code
        ['view_sourcesofauthority', 'agents', 'sourcesofauthority'],  # Can view sources of authority
        ['view_topography', 'agents', 'topography'],  # Can view topography
        ['add_informationpackage', 'ip', 'informationpackage'],  # Can add information package
        ['delete_informationpackage', 'ip', 'informationpackage'],  # Can delete information package
        ['view_informationpackage', 'ip', 'informationpackage'],  # Can view information package
        ['transfer_sip', 'ip', 'informationpackage'],  # Can transfer SIP
        ['change_sa', 'ip', 'informationpackage'],  # Can change SA connected to IP
        ['lock_sa', 'ip', 'informationpackage'],  # Can lock SA to IP
        ['receive', 'ip', 'informationpackage'],  # Can receive IP
        ['preserve', 'ip', 'informationpackage'],  # Can preserve IP
        ['preserve_dip', 'ip', 'informationpackage'],  # Can preserve DIP
        ['get_from_storage', 'ip', 'informationpackage'],  # Can get extracted IP from storage
        ['get_tar_from_storage', 'ip', 'informationpackage'],  # Can get packaged IP from storage
        ['get_from_storage_as_new', 'ip', 'informationpackage'],  # Can get IP "as new" from storage
        ['add_to_ingest_workarea', 'ip', 'informationpackage'],  # Can add IP to ingest workarea
        ['add_to_ingest_workarea_as_tar', 'ip', 'informationpackage'],  # Can add IP as tar to ingest workarea
        ['add_to_ingest_workarea_as_new', 'ip',
            'informationpackage'],  # Can add IP as new generation to ingest workarea
        ['diff-check', 'ip', 'informationpackage'],  # Can diff-check IP
        ['query', 'ip', 'informationpackage'],  # Can query IP
        ['delete_first_generation', 'ip', 'informationpackage'],  # Can delete first generation of IP
        ['delete_last_generation', 'ip', 'informationpackage'],  # Can delete last generation of IP
        ['delete_archived', 'ip', 'informationpackage'],  # Can delete archived IP
        ['see_all_in_workspaces', 'ip', 'informationpackage'],  # Can see all IPs workspaces
        ['see_other_user_ip_files', 'ip', 'informationpackage'],  # Can see files in other users IPs
        ['add_workarea', 'ip', 'workarea'],  # Can add workarea
        ['change_workarea', 'ip', 'workarea'],  # Can change workarea
        ['delete_workarea', 'ip', 'workarea'],  # Can delete workarea
        ['view_workarea', 'ip', 'workarea'],  # Can view workarea
        ['move_from_ingest_workarea', 'ip', 'workarea'],  # Can move IP from ingest workarea
        ['move_from_access_workarea', 'ip', 'workarea'],  # Can move IP from access workarea
        ['preserve_from_ingest_workarea', 'ip', 'workarea'],  # Can preserve IP from ingest workarea
        ['preserve_from_access_workarea', 'ip', 'workarea'],  # Can preserve IP from access workarea
        ['add_order', 'ip', 'order'],  # Can add order
        ['change_order', 'ip', 'order'],  # Can change order
        ['delete_order', 'ip', 'order'],  # Can delete order
        ['view_order', 'ip', 'order'],  # Can view order
        ['prepare_order', 'ip', 'order'],  # Can prepare order
        ['add_eventip', 'ip', 'eventip'],  # Can add Events related to IP
        ['add_ordertype', 'ip', 'ordertype'],  # Can add order type
        ['change_ordertype', 'ip', 'ordertype'],  # Can change order type
        ['delete_ordertype', 'ip', 'ordertype'],  # Can delete order type
        ['view_ordertype', 'ip', 'ordertype'],  # Can view order type
        ['view_submissionagreement', 'profiles', 'submissionagreement'],  # Can view submission agreement
        ['export_sa', 'profiles', 'submissionagreement'],  # Can export SA
        ['view_profile', 'profiles', 'profile'],  # Can view profile
        ['change_profileip', 'profiles', 'profileip'],  # Can change profile ip
        ['view_profileip', 'profiles', 'profileip'],  # Can view profile ip
        ['add_profileipdata', 'profiles', 'profileipdata'],  # Can add profile ip data
        ['view_submissionagreementipdata', 'profiles',
            'submissionagreementipdata'],  # Can view submission agreement ip data
        ['add_extensionpackage', 'ProfileMaker', 'extensionpackage'],  # Can add extension package
        ['add_appraisaljob', 'maintenance', 'appraisaljob'],  # Can add appraisal job
        ['change_appraisaljob', 'maintenance', 'appraisaljob'],  # Can change appraisal job
        ['delete_appraisaljob', 'maintenance', 'appraisaljob'],  # Can delete appraisal job
        ['view_appraisaljob', 'maintenance', 'appraisaljob'],  # Can view appraisal job
        ['run_appraisaljob', 'maintenance', 'appraisaljob'],  # Can run appraisal job
        ['add_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can add appraisal job entry
        ['change_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can change appraisal job entry
        ['delete_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can delete appraisal job entry
        ['view_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can view appraisal job entry
        ['add_conversionjob', 'maintenance', 'conversionjob'],  # Can add conversion job
        ['change_conversionjob', 'maintenance', 'conversionjob'],  # Can change conversion job
        ['delete_conversionjob', 'maintenance', 'conversionjob'],  # Can delete conversion job
        ['view_conversionjob', 'maintenance', 'conversionjob'],  # Can view conversion job
        ['run_conversionjob', 'maintenance', 'conversionjob'],  # Can run conversion job
        ['add_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can add conversion job entry
        ['change_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can change conversion job entry
        ['delete_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can delete conversion job entry
        ['view_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can view conversion job entry
        ['add_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can add appraisal template
        ['change_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can change appraisal template
        ['delete_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can delete appraisal template
        ['view_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can view appraisal template
        ['add_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can add conversion template
        ['change_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can change conversion template
        ['delete_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can delete conversion template
        ['view_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can view conversion template
        ['view_tag', 'tags', 'tag'],  # Can view tag
        ['search', 'tags', 'tag'],  # Can search
        ['view_structure', 'tags', 'structure'],  # Can view structure
        ['view_tagstructure', 'tags', 'tagstructure'],  # Can view tag structure
        ['view_tagversion', 'tags', 'tagversion'],  # Can view tag version
        ['view_structureunit', 'tags', 'structureunit'],  # Can view structure unit
        ['view_mediumtype', 'tags', 'mediumtype'],  # Can view medium type
        ['view_nodeidentifier', 'tags', 'nodeidentifier'],  # Can view node identifier
        ['view_nodenote', 'tags', 'nodenote'],  # Can view node note
        ['view_nodenotetype', 'tags', 'nodenotetype'],  # Can view node note type
        ['view_noderelationtype', 'tags', 'noderelationtype'],  # Can view node relation type
        ['view_ruleconventiontype', 'tags', 'ruleconventiontype'],  # Can view rule convention type
        ['view_structuretype', 'tags', 'structuretype'],  # Can view structure type
        ['view_structureunitrelation', 'tags', 'structureunitrelation'],  # Can view structure unit relation
        ['view_structureunittype', 'tags', 'structureunittype'],  # Can view structure unit type
        ['view_tagversionrelation', 'tags', 'tagversionrelation'],  # Can view tag version relation
        ['view_search', 'tags', 'search'],  # Can view search
        ['view_tagversiontype', 'tags', 'tagversiontype'],  # Can view node type
        ['view_location', 'tags', 'location'],  # Can view location
        ['view_locationfunctiontype', 'tags', 'locationfunctiontype'],  # Can view location function type
        ['view_locationleveltype', 'tags', 'locationleveltype'],  # Can view location level type
        ['view_metrictype', 'tags', 'metrictype'],  # Can view metric type
        ['view_delivery', 'tags', 'delivery'],  # Can view delivery
        ['view_deliverytype', 'tags', 'deliverytype'],  # Can view delivery type
        ['view_transfer', 'tags', 'transfer'],  # Can view transfer
        ['view_structurerelationtype', 'tags', 'structurerelationtype'],  # Can view structure relation type
        ['view_structurerelation', 'tags', 'structurerelation'],  # Can view structure relation
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_archivist.permissions.add(p_obj)

    role_administrator, _ = GroupMemberRole.objects.get_or_create(codename='Administrator')
    permission_list_user = [
        ['add_agent', 'agents', 'agent'],  # Can add agent
        ['change_agent', 'agents', 'agent'],  # Can change agent
        ['delete_agent', 'agents', 'agent'],  # Can delete agent
        ['view_agent', 'agents', 'agent'],  # Can view agent
        ['add_agentfunction', 'agents', 'agentfunction'],  # Can add agent function
        ['change_agentfunction', 'agents', 'agentfunction'],  # Can change agent function
        ['delete_agentfunction', 'agents', 'agentfunction'],  # Can delete agent function
        ['view_agentfunction', 'agents', 'agentfunction'],  # Can view agent function
        ['add_agentidentifier', 'agents', 'agentidentifier'],  # Can add agent identifier
        ['change_agentidentifier', 'agents', 'agentidentifier'],  # Can change agent identifier
        ['delete_agentidentifier', 'agents', 'agentidentifier'],  # Can delete agent identifier
        ['view_agentidentifier', 'agents', 'agentidentifier'],  # Can view agent identifier
        ['add_agentidentifiertype', 'agents', 'agentidentifiertype'],  # Can add agent identifier type
        ['change_agentidentifiertype', 'agents', 'agentidentifiertype'],  # Can change agent identifier type
        ['delete_agentidentifiertype', 'agents', 'agentidentifiertype'],  # Can delete agent identifier type
        ['view_agentidentifiertype', 'agents', 'agentidentifiertype'],  # Can view agent identifier type
        ['add_agentname', 'agents', 'agentname'],  # Can add agent name
        ['change_agentname', 'agents', 'agentname'],  # Can change agent name
        ['delete_agentname', 'agents', 'agentname'],  # Can delete agent name
        ['view_agentname', 'agents', 'agentname'],  # Can view agent name
        ['add_agentnametype', 'agents', 'agentnametype'],  # Can add agent name type
        ['change_agentnametype', 'agents', 'agentnametype'],  # Can change agent name type
        ['delete_agentnametype', 'agents', 'agentnametype'],  # Can delete agent name type
        ['view_agentnametype', 'agents', 'agentnametype'],  # Can view agent name type
        ['add_agentnote', 'agents', 'agentnote'],  # Can add agent note
        ['change_agentnote', 'agents', 'agentnote'],  # Can change agent note
        ['delete_agentnote', 'agents', 'agentnote'],  # Can delete agent note
        ['view_agentnote', 'agents', 'agentnote'],  # Can view agent note
        ['add_agentnotetype', 'agents', 'agentnotetype'],  # Can add agent note type
        ['change_agentnotetype', 'agents', 'agentnotetype'],  # Can change agent note type
        ['delete_agentnotetype', 'agents', 'agentnotetype'],  # Can delete agent note type
        ['view_agentnotetype', 'agents', 'agentnotetype'],  # Can view agent note type
        ['add_agentplace', 'agents', 'agentplace'],  # Can add agent place
        ['change_agentplace', 'agents', 'agentplace'],  # Can change agent place
        ['delete_agentplace', 'agents', 'agentplace'],  # Can delete agent place
        ['view_agentplace', 'agents', 'agentplace'],  # Can view agent place
        ['add_agentplacetype', 'agents', 'agentplacetype'],  # Can add agent place type
        ['change_agentplacetype', 'agents', 'agentplacetype'],  # Can change agent place type
        ['delete_agentplacetype', 'agents', 'agentplacetype'],  # Can delete agent place type
        ['view_agentplacetype', 'agents', 'agentplacetype'],  # Can view agent place type
        ['add_agentrelation', 'agents', 'agentrelation'],  # Can add agent relation
        ['change_agentrelation', 'agents', 'agentrelation'],  # Can change agent relation
        ['delete_agentrelation', 'agents', 'agentrelation'],  # Can delete agent relation
        ['view_agentrelation', 'agents', 'agentrelation'],  # Can view agent relation
        ['add_agentrelationtype', 'agents', 'agentrelationtype'],  # Can add agent relation type
        ['change_agentrelationtype', 'agents', 'agentrelationtype'],  # Can change agent relation type
        ['delete_agentrelationtype', 'agents', 'agentrelationtype'],  # Can delete agent relation type
        ['view_agentrelationtype', 'agents', 'agentrelationtype'],  # Can view agent relation type
        ['add_agenttaglink', 'agents', 'agenttaglink'],  # Can add Agent node relation
        ['change_agenttaglink', 'agents', 'agenttaglink'],  # Can change Agent node relation
        ['delete_agenttaglink', 'agents', 'agenttaglink'],  # Can delete Agent node relation
        ['view_agenttaglink', 'agents', 'agenttaglink'],  # Can view Agent node relation
        ['add_agenttaglinkrelationtype', 'agents', 'agenttaglinkrelationtype'],  # Can add agent tag relation type
        ['change_agenttaglinkrelationtype', 'agents',
            'agenttaglinkrelationtype'],  # Can change agent tag relation type
        ['delete_agenttaglinkrelationtype', 'agents',
            'agenttaglinkrelationtype'],  # Can delete agent tag relation type
        ['view_agenttaglinkrelationtype', 'agents', 'agenttaglinkrelationtype'],  # Can view agent tag relation type
        ['add_agenttype', 'agents', 'agenttype'],  # Can add agent type
        ['change_agenttype', 'agents', 'agenttype'],  # Can change agent type
        ['delete_agenttype', 'agents', 'agenttype'],  # Can delete agent type
        ['view_agenttype', 'agents', 'agenttype'],  # Can view agent type
        ['add_authoritytype', 'agents', 'authoritytype'],  # Can add authority type
        ['change_authoritytype', 'agents', 'authoritytype'],  # Can change authority type
        ['delete_authoritytype', 'agents', 'authoritytype'],  # Can delete authority type
        ['view_authoritytype', 'agents', 'authoritytype'],  # Can view authority type
        ['add_mainagenttype', 'agents', 'mainagenttype'],  # Can add main agent type
        ['change_mainagenttype', 'agents', 'mainagenttype'],  # Can change main agent type
        ['delete_mainagenttype', 'agents', 'mainagenttype'],  # Can delete main agent type
        ['view_mainagenttype', 'agents', 'mainagenttype'],  # Can view main agent type
        ['add_refcode', 'agents', 'refcode'],  # Can add ref code
        ['change_refcode', 'agents', 'refcode'],  # Can change ref code
        ['delete_refcode', 'agents', 'refcode'],  # Can delete ref code
        ['view_refcode', 'agents', 'refcode'],  # Can view ref code
        ['add_sourcesofauthority', 'agents', 'sourcesofauthority'],  # Can add sources of authority
        ['change_sourcesofauthority', 'agents', 'sourcesofauthority'],  # Can change sources of authority
        ['delete_sourcesofauthority', 'agents', 'sourcesofauthority'],  # Can delete sources of authority
        ['view_sourcesofauthority', 'agents', 'sourcesofauthority'],  # Can view sources of authority
        ['add_topography', 'agents', 'topography'],  # Can add topography
        ['change_topography', 'agents', 'topography'],  # Can change topography
        ['delete_topography', 'agents', 'topography'],  # Can delete topography
        ['view_topography', 'agents', 'topography'],  # Can view topography
        ['add_informationpackage', 'ip', 'informationpackage'],  # Can add information package
        ['delete_informationpackage', 'ip', 'informationpackage'],  # Can delete information package
        ['view_informationpackage', 'ip', 'informationpackage'],  # Can view information package
        ['transfer_sip', 'ip', 'informationpackage'],  # Can transfer SIP
        ['change_sa', 'ip', 'informationpackage'],  # Can change SA connected to IP
        ['lock_sa', 'ip', 'informationpackage'],  # Can lock SA to IP
        ['receive', 'ip', 'informationpackage'],  # Can receive IP
        ['preserve', 'ip', 'informationpackage'],  # Can preserve IP
        ['preserve_dip', 'ip', 'informationpackage'],  # Can preserve DIP
        ['get_from_storage', 'ip', 'informationpackage'],  # Can get extracted IP from storage
        ['get_tar_from_storage', 'ip', 'informationpackage'],  # Can get packaged IP from storage
        ['get_from_storage_as_new', 'ip', 'informationpackage'],  # Can get IP "as new" from storage
        ['add_to_ingest_workarea', 'ip', 'informationpackage'],  # Can add IP to ingest workarea
        ['add_to_ingest_workarea_as_tar', 'ip', 'informationpackage'],  # Can add IP as tar to ingest workarea
        ['add_to_ingest_workarea_as_new', 'ip',
            'informationpackage'],  # Can add IP as new generation to ingest workarea
        ['diff-check', 'ip', 'informationpackage'],  # Can diff-check IP
        ['query', 'ip', 'informationpackage'],  # Can query IP
        ['delete_first_generation', 'ip', 'informationpackage'],  # Can delete first generation of IP
        ['delete_last_generation', 'ip', 'informationpackage'],  # Can delete last generation of IP
        ['delete_archived', 'ip', 'informationpackage'],  # Can delete archived IP
        ['see_all_in_workspaces', 'ip', 'informationpackage'],  # Can see all IPs workspaces
        ['see_other_user_ip_files', 'ip', 'informationpackage'],  # Can see files in other users IPs
        ['add_workarea', 'ip', 'workarea'],  # Can add workarea
        ['change_workarea', 'ip', 'workarea'],  # Can change workarea
        ['delete_workarea', 'ip', 'workarea'],  # Can delete workarea
        ['view_workarea', 'ip', 'workarea'],  # Can view workarea
        ['move_from_ingest_workarea', 'ip', 'workarea'],  # Can move IP from ingest workarea
        ['move_from_access_workarea', 'ip', 'workarea'],  # Can move IP from access workarea
        ['preserve_from_ingest_workarea', 'ip', 'workarea'],  # Can preserve IP from ingest workarea
        ['preserve_from_access_workarea', 'ip', 'workarea'],  # Can preserve IP from access workarea
        ['add_order', 'ip', 'order'],  # Can add order
        ['change_order', 'ip', 'order'],  # Can change order
        ['delete_order', 'ip', 'order'],  # Can delete order
        ['view_order', 'ip', 'order'],  # Can view order
        ['prepare_order', 'ip', 'order'],  # Can prepare order
        ['add_eventip', 'ip', 'eventip'],  # Can add Events related to IP
        ['add_ordertype', 'ip', 'ordertype'],  # Can add order type
        ['change_ordertype', 'ip', 'ordertype'],  # Can change order type
        ['delete_ordertype', 'ip', 'ordertype'],  # Can delete order type
        ['view_ordertype', 'ip', 'ordertype'],  # Can view order type
        ['add_submissionagreement', 'profiles', 'submissionagreement'],  # Can add submission agreement
        ['change_submissionagreement', 'profiles', 'submissionagreement'],  # Can change submission agreement
        ['delete_submissionagreement', 'profiles', 'submissionagreement'],  # Can delete submission agreement
        ['view_submissionagreement', 'profiles', 'submissionagreement'],  # Can view submission agreement
        ['create_new_sa_generation', 'profiles', 'submissionagreement'],  # Can create new generations of SA
        ['export_sa', 'profiles', 'submissionagreement'],  # Can export SA
        ['add_profile', 'profiles', 'profile'],  # Can add profile
        ['change_profile', 'profiles', 'profile'],  # Can change profile
        ['view_profile', 'profiles', 'profile'],  # Can view profile
        ['change_profileip', 'profiles', 'profileip'],  # Can change profile ip
        ['view_profileip', 'profiles', 'profileip'],  # Can view profile ip
        ['add_profileipdata', 'profiles', 'profileipdata'],  # Can add profile ip data
        # Can change submission agreement ip data
        ['change_submissionagreementipdata', 'profiles', 'submissionagreementipdata'],
        # Can delete submission agreement ip data
        ['delete_submissionagreementipdata', 'profiles', 'submissionagreementipdata'],
        ['view_submissionagreementipdata', 'profiles',
            'submissionagreementipdata'],  # Can view submission agreement ip data
        ['add_extensionpackage', 'ProfileMaker', 'extensionpackage'],  # Can add extension package
        ['add_appraisaljob', 'maintenance', 'appraisaljob'],  # Can add appraisal job
        ['change_appraisaljob', 'maintenance', 'appraisaljob'],  # Can change appraisal job
        ['delete_appraisaljob', 'maintenance', 'appraisaljob'],  # Can delete appraisal job
        ['view_appraisaljob', 'maintenance', 'appraisaljob'],  # Can view appraisal job
        ['run_appraisaljob', 'maintenance', 'appraisaljob'],  # Can run appraisal job
        ['add_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can add appraisal job entry
        ['change_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can change appraisal job entry
        ['delete_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can delete appraisal job entry
        ['view_appraisaljobentry', 'maintenance', 'appraisaljobentry'],  # Can view appraisal job entry
        ['add_conversionjob', 'maintenance', 'conversionjob'],  # Can add conversion job
        ['change_conversionjob', 'maintenance', 'conversionjob'],  # Can change conversion job
        ['delete_conversionjob', 'maintenance', 'conversionjob'],  # Can delete conversion job
        ['view_conversionjob', 'maintenance', 'conversionjob'],  # Can view conversion job
        ['run_conversionjob', 'maintenance', 'conversionjob'],  # Can run conversion job
        ['add_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can add conversion job entry
        ['change_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can change conversion job entry
        ['delete_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can delete conversion job entry
        ['view_conversionjobentry', 'maintenance', 'conversionjobentry'],  # Can view conversion job entry
        ['add_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can add appraisal template
        ['change_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can change appraisal template
        ['delete_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can delete appraisal template
        ['view_appraisaltemplate', 'maintenance', 'appraisaltemplate'],  # Can view appraisal template
        ['add_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can add conversion template
        ['change_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can change conversion template
        ['delete_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can delete conversion template
        ['view_conversiontemplate', 'maintenance', 'conversiontemplate'],  # Can view conversion template
        ['storage_migration', 'storage', 'storageobject'],  # Storage migration
        ['storage_maintenance', 'storage', 'storageobject'],  # Storage maintenance
        ['storage_management', 'storage', 'storageobject'],  # Storage management
        ['add_tag', 'tags', 'tag'],  # Can add tag
        ['change_tag', 'tags', 'tag'],  # Can change tag
        ['delete_tag', 'tags', 'tag'],  # Can delete tag
        ['view_tag', 'tags', 'tag'],  # Can view tag
        ['search', 'tags', 'tag'],  # Can search
        ['create_archive', 'tags', 'tag'],  # Can create new archives
        ['change_archive', 'tags', 'tag'],  # Can change archives
        ['delete_archive', 'tags', 'tag'],  # Can delete archives
        ['change_tag_location', 'tags', 'tag'],  # Can change tag location
        ['security_level_1', 'tags', 'tag'],  # Can see security level 1
        ['security_level_exists_1', 'tags', 'tag'],  # Can see security level 1 exists
        ['security_level_2', 'tags', 'tag'],  # Can see security level 2
        ['security_level_exists_2', 'tags', 'tag'],  # Can see security level 2 exists
        ['security_level_3', 'tags', 'tag'],  # Can see security level 3
        ['security_level_exists_3', 'tags', 'tag'],  # Can see security level 3 exists
        ['security_level_4', 'tags', 'tag'],  # Can see security level 4
        ['security_level_exists_4', 'tags', 'tag'],  # Can see security level 4 exists
        ['security_level_5', 'tags', 'tag'],  # Can see security level 5
        ['security_level_exists_5', 'tags', 'tag'],  # Can see security level 5 exists
        ['add_structure', 'tags', 'structure'],  # Can add structure
        ['change_structure', 'tags', 'structure'],  # Can change structure
        ['delete_structure', 'tags', 'structure'],  # Can delete structure
        ['view_structure', 'tags', 'structure'],  # Can view structure
        ['publish_structure', 'tags', 'structure'],  # Can publish structures
        ['unpublish_structure', 'tags', 'structure'],  # Can unpublish structures
        ['create_new_structure_version', 'tags', 'structure'],  # Can create new structure versions
        ['add_tagstructure', 'tags', 'tagstructure'],  # Can add tag structure
        ['change_tagstructure', 'tags', 'tagstructure'],  # Can change tag structure
        ['delete_tagstructure', 'tags', 'tagstructure'],  # Can delete tag structure
        ['view_tagstructure', 'tags', 'tagstructure'],  # Can view tag structure
        ['add_tagversion', 'tags', 'tagversion'],  # Can add tag version
        ['change_tagversion', 'tags', 'tagversion'],  # Can change tag version
        ['delete_tagversion', 'tags', 'tagversion'],  # Can delete tag version
        ['view_tagversion', 'tags', 'tagversion'],  # Can view tag version
        ['add_structureunit', 'tags', 'structureunit'],  # Can add structure unit
        ['change_structureunit', 'tags', 'structureunit'],  # Can change structure unit
        ['delete_structureunit', 'tags', 'structureunit'],  # Can delete structure unit
        ['view_structureunit', 'tags', 'structureunit'],  # Can view structure unit
        ['add_structureunit_instance', 'tags', 'structureunit'],  # Can add structure unit instances
        ['change_structureunit_instance', 'tags', 'structureunit'],  # Can change instances of structure units
        ['delete_structureunit_instance', 'tags', 'structureunit'],  # Can delete instances of structure units
        ['move_structureunit_instance', 'tags', 'structureunit'],  # Can move instances of structure units
        ['add_mediumtype', 'tags', 'mediumtype'],  # Can add medium type
        ['change_mediumtype', 'tags', 'mediumtype'],  # Can change medium type
        ['delete_mediumtype', 'tags', 'mediumtype'],  # Can delete medium type
        ['view_mediumtype', 'tags', 'mediumtype'],  # Can view medium type
        ['add_nodeidentifier', 'tags', 'nodeidentifier'],  # Can add node identifier
        ['change_nodeidentifier', 'tags', 'nodeidentifier'],  # Can change node identifier
        ['delete_nodeidentifier', 'tags', 'nodeidentifier'],  # Can delete node identifier
        ['view_nodeidentifier', 'tags', 'nodeidentifier'],  # Can view node identifier
        ['add_nodeidentifiertype', 'tags', 'nodeidentifiertype'],  # Can add node identifier type
        ['change_nodeidentifiertype', 'tags', 'nodeidentifiertype'],  # Can change node identifier type
        ['delete_nodeidentifiertype', 'tags', 'nodeidentifiertype'],  # Can delete node identifier type
        ['view_nodeidentifiertype', 'tags', 'nodeidentifiertype'],  # Can view node identifier type
        ['add_nodenote', 'tags', 'nodenote'],  # Can add node note
        ['change_nodenote', 'tags', 'nodenote'],  # Can change node note
        ['delete_nodenote', 'tags', 'nodenote'],  # Can delete node note
        ['view_nodenote', 'tags', 'nodenote'],  # Can view node note
        ['add_nodenotetype', 'tags', 'nodenotetype'],  # Can add node note type
        ['change_nodenotetype', 'tags', 'nodenotetype'],  # Can change node note type
        ['delete_nodenotetype', 'tags', 'nodenotetype'],  # Can delete node note type
        ['view_nodenotetype', 'tags', 'nodenotetype'],  # Can view node note type
        ['add_noderelationtype', 'tags', 'noderelationtype'],  # Can add node relation type
        ['change_noderelationtype', 'tags', 'noderelationtype'],  # Can change node relation type
        ['delete_noderelationtype', 'tags', 'noderelationtype'],  # Can delete node relation type
        ['view_noderelationtype', 'tags', 'noderelationtype'],  # Can view node relation type
        ['add_ruleconventiontype', 'tags', 'ruleconventiontype'],  # Can add rule convention type
        ['change_ruleconventiontype', 'tags', 'ruleconventiontype'],  # Can change rule convention type
        ['delete_ruleconventiontype', 'tags', 'ruleconventiontype'],  # Can delete rule convention type
        ['view_ruleconventiontype', 'tags', 'ruleconventiontype'],  # Can view rule convention type
        ['add_structuretype', 'tags', 'structuretype'],  # Can add structure type
        ['change_structuretype', 'tags', 'structuretype'],  # Can change structure type
        ['delete_structuretype', 'tags', 'structuretype'],  # Can delete structure type
        ['view_structuretype', 'tags', 'structuretype'],  # Can view structure type
        ['add_structureunitrelation', 'tags', 'structureunitrelation'],  # Can add structure unit relation
        ['change_structureunitrelation', 'tags', 'structureunitrelation'],  # Can change structure unit relation
        ['delete_structureunitrelation', 'tags', 'structureunitrelation'],  # Can delete structure unit relation
        ['view_structureunitrelation', 'tags', 'structureunitrelation'],  # Can view structure unit relation
        ['add_structureunittype', 'tags', 'structureunittype'],  # Can add structure unit type
        ['change_structureunittype', 'tags', 'structureunittype'],  # Can change structure unit type
        ['delete_structureunittype', 'tags', 'structureunittype'],  # Can delete structure unit type
        ['view_structureunittype', 'tags', 'structureunittype'],  # Can view structure unit type
        ['add_tagversionrelation', 'tags', 'tagversionrelation'],  # Can add tag version relation
        ['change_tagversionrelation', 'tags', 'tagversionrelation'],  # Can change tag version relation
        ['delete_tagversionrelation', 'tags', 'tagversionrelation'],  # Can delete tag version relation
        ['view_tagversionrelation', 'tags', 'tagversionrelation'],  # Can view tag version relation
        ['add_search', 'tags', 'search'],  # Can add search
        ['change_search', 'tags', 'search'],  # Can change search
        ['delete_search', 'tags', 'search'],  # Can delete search
        ['view_search', 'tags', 'search'],  # Can view search
        ['add_tagversiontype', 'tags', 'tagversiontype'],  # Can add node type
        ['change_tagversiontype', 'tags', 'tagversiontype'],  # Can change node type
        ['delete_tagversiontype', 'tags', 'tagversiontype'],  # Can delete node type
        ['view_tagversiontype', 'tags', 'tagversiontype'],  # Can view node type
        ['add_location', 'tags', 'location'],  # Can add location
        ['change_location', 'tags', 'location'],  # Can change location
        ['delete_location', 'tags', 'location'],  # Can delete location
        ['view_location', 'tags', 'location'],  # Can view location
        ['add_locationfunctiontype', 'tags', 'locationfunctiontype'],  # Can add location function type
        ['change_locationfunctiontype', 'tags', 'locationfunctiontype'],  # Can change location function type
        ['delete_locationfunctiontype', 'tags', 'locationfunctiontype'],  # Can delete location function type
        ['view_locationfunctiontype', 'tags', 'locationfunctiontype'],  # Can view location function type
        ['add_locationleveltype', 'tags', 'locationleveltype'],  # Can add location level type
        ['change_locationleveltype', 'tags', 'locationleveltype'],  # Can change location level type
        ['delete_locationleveltype', 'tags', 'locationleveltype'],  # Can delete location level type
        ['view_locationleveltype', 'tags', 'locationleveltype'],  # Can view location level type
        ['add_metrictype', 'tags', 'metrictype'],  # Can add metric type
        ['change_metrictype', 'tags', 'metrictype'],  # Can change metric type
        ['delete_metrictype', 'tags', 'metrictype'],  # Can delete metric type
        ['view_metrictype', 'tags', 'metrictype'],  # Can view metric type
        ['add_delivery', 'tags', 'delivery'],  # Can add delivery
        ['change_delivery', 'tags', 'delivery'],  # Can change delivery
        ['delete_delivery', 'tags', 'delivery'],  # Can delete delivery
        ['view_delivery', 'tags', 'delivery'],  # Can view delivery
        ['add_deliverytype', 'tags', 'deliverytype'],  # Can add delivery type
        ['change_deliverytype', 'tags', 'deliverytype'],  # Can change delivery type
        ['delete_deliverytype', 'tags', 'deliverytype'],  # Can delete delivery type
        ['view_deliverytype', 'tags', 'deliverytype'],  # Can view delivery type
        ['add_transfer', 'tags', 'transfer'],  # Can add transfer
        ['change_transfer', 'tags', 'transfer'],  # Can change transfer
        ['delete_transfer', 'tags', 'transfer'],  # Can delete transfer
        ['view_transfer', 'tags', 'transfer'],  # Can view transfer
        ['add_structurerelationtype', 'tags', 'structurerelationtype'],  # Can add structure relation type
        ['change_structurerelationtype', 'tags', 'structurerelationtype'],  # Can change structure relation type
        ['delete_structurerelationtype', 'tags', 'structurerelationtype'],  # Can delete structure relation type
        ['view_structurerelationtype', 'tags', 'structurerelationtype'],  # Can view structure relation type
        ['add_structurerelation', 'tags', 'structurerelation'],  # Can add structure relation
        ['change_structurerelation', 'tags', 'structurerelation'],  # Can change structure relation
        ['delete_structurerelation', 'tags', 'structurerelation'],  # Can delete structure relation
        ['view_structurerelation', 'tags', 'structurerelation'],  # Can view structure relation
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0], content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_administrator.permissions.add(p_obj)

    role_system_administrator, _ = GroupMemberRole.objects.get_or_create(codename='System Administrator')
    permission_list_user = [
        ['add_emailaddress', 'account', 'emailaddress'],  # Can add email address
        ['change_emailaddress', 'account', 'emailaddress'],  # Can change email address
        ['delete_emailaddress', 'account', 'emailaddress'],  # Can delete email address
        ['view_emailaddress', 'account', 'emailaddress'],  # Can view email address
        ['add_emailconfirmation', 'account', 'emailconfirmation'],  # Can add email confirmation
        ['change_emailconfirmation', 'account', 'emailconfirmation'],  # Can change email confirmation
        ['delete_emailconfirmation', 'account', 'emailconfirmation'],  # Can delete email confirmation
        ['view_emailconfirmation', 'account', 'emailconfirmation'],  # Can view email confirmation
        ['add_logentry', 'admin', 'logentry'],  # Can add log entry
        ['change_logentry', 'admin', 'logentry'],  # Can change log entry
        ['delete_logentry', 'admin', 'logentry'],  # Can delete log entry
        ['view_logentry', 'admin', 'logentry'],  # Can view log entry
        ['add_permission', 'auth', 'permission'],  # Can add permission
        ['change_permission', 'auth', 'permission'],  # Can change permission
        ['delete_permission', 'auth', 'permission'],  # Can delete permission
        ['view_permission', 'auth', 'permission'],  # Can view permission
        ['add_group', 'auth', 'group'],  # Can add group
        ['change_group', 'auth', 'group'],  # Can change group
        ['delete_group', 'auth', 'group'],  # Can delete group
        ['view_group', 'auth', 'group'],  # Can view group
        ['add_user', 'auth', 'user'],  # Can add user
        ['change_user', 'auth', 'user'],  # Can change user
        ['delete_user', 'auth', 'user'],  # Can delete user
        ['view_user', 'auth', 'user'],  # Can view user
        ['add_grouptype', 'groups_manager', 'grouptype'],  # Can add group type
        ['change_grouptype', 'groups_manager', 'grouptype'],  # Can change group type
        ['delete_grouptype', 'groups_manager', 'grouptype'],  # Can delete group type
        ['add_groupmemberrole', 'essauth', 'groupmemberrole'],  # Can add role
        ['change_groupmemberrole', 'essauth', 'groupmemberrole'],  # Can change role
        ['delete_groupmemberrole', 'essauth', 'groupmemberrole'],  # Can delete role
        ['assign_groupmemberrole', 'essauth', 'groupmemberrole'],  # Can assign roles
        ['add_eventtype', 'configuration', 'eventtype'],  # Can add Event Type
        ['change_eventtype', 'configuration', 'eventtype'],  # Can change Event Type
        ['delete_eventtype', 'configuration', 'eventtype'],  # Can delete Event Type
        ['add_parameter', 'configuration', 'parameter'],  # Can add parameter
        ['change_parameter', 'configuration', 'parameter'],  # Can change parameter
        ['delete_parameter', 'configuration', 'parameter'],  # Can delete parameter
        ['add_path', 'configuration', 'path'],  # Can add path
        ['change_path', 'configuration', 'path'],  # Can change path
        ['delete_path', 'configuration', 'path'],  # Can delete path
        ['add_storagepolicy', 'configuration', 'storagepolicy'],  # Can add storage policy
        ['change_storagepolicy', 'configuration', 'storagepolicy'],  # Can change storage policy
        ['delete_storagepolicy', 'configuration', 'storagepolicy'],  # Can delete storage policy
        ['add_submissionagreement', 'profiles', 'submissionagreement'],  # Can add submission agreement
        ['change_submissionagreement', 'profiles', 'submissionagreement'],  # Can change submission agreement
        ['delete_submissionagreement', 'profiles', 'submissionagreement'],  # Can delete submission agreement
        ['add_profile', 'profiles', 'profile'],  # Can add profile
        ['change_profile', 'profiles', 'profile'],  # Can change profile
        ['delete_profile', 'profiles', 'profile'],  # Can delete profile
        ['change_ioqueue', 'storage', 'ioqueue'],  # Can change io queue
        ['delete_ioqueue', 'storage', 'ioqueue'],  # Can delete io queue
        ['add_storagemethod', 'storage', 'storagemethod'],  # Can add storage method
        ['change_storagemethod', 'storage', 'storagemethod'],  # Can change storage method
        ['delete_storagemethod', 'storage', 'storagemethod'],  # Can delete storage method
        # Can add Storage Method/Target Relation
        ['add_storagemethodtargetrelation', 'storage', 'storagemethodtargetrelation'],
        # Can change Storage Method/Target Relation
        ['change_storagemethodtargetrelation', 'storage', 'storagemethodtargetrelation'],
        # Can delete Storage Method/Target Relation
        ['delete_storagemethodtargetrelation', 'storage', 'storagemethodtargetrelation'],
        ['storage_migration', 'storage', 'storageobject'],  # Storage migration
        ['storage_maintenance', 'storage', 'storageobject'],  # Storage maintenance
        ['storage_management', 'storage', 'storageobject'],  # Storage management
        ['add_storagetarget', 'storage', 'storagetarget'],  # Can add Storage Target
        ['change_storagetarget', 'storage', 'storagetarget'],  # Can change Storage Target
        ['delete_storagetarget', 'storage', 'storagetarget'],  # Can delete Storage Target
        ['add_robot', 'storage', 'robot'],  # Can add robot
        ['change_robot', 'storage', 'robot'],  # Can change robot
        ['delete_robot', 'storage', 'robot'],  # Can delete robot
        ['change_robotqueue', 'storage', 'robotqueue'],  # Can change robot queue
        ['delete_robotqueue', 'storage', 'robotqueue'],  # Can delete robot queue
        ['add_tapedrive', 'storage', 'tapedrive'],  # Can add tape drive
        ['change_tapedrive', 'storage', 'tapedrive'],  # Can change tape drive
        ['delete_tapedrive', 'storage', 'tapedrive'],  # Can delete tape drive
    ]

    for p in permission_list_user:
        p_obj = Permission.objects.get(
            codename=p[0],
            content_type__app_label=p[1],
            content_type__model=p[2],
        )
        role_system_administrator.permissions.add(p_obj)

    #####################################
    # Users
    # click.echo('Installing Users ...')

    user_user, created = User.objects.get_or_create(
        first_name='User', last_name='Lastname',
        username='user', email='user@essolutions.se'
    )
    if created:
        user_user.set_password('user')
        user_user.save()
        default_org.add_member(user_user.essauth_member, roles=[role_user])

    user_producer, created = User.objects.get_or_create(
        first_name='Producer', last_name='Lastname',
        username='producer', email='producer@essolutions.se'
    )
    if created:
        user_producer.set_password('producer')
        user_producer.save()
        default_org.add_member(user_producer.essauth_member, roles=[role_producer])

    user_submitter, created = User.objects.get_or_create(
        first_name='Submitter', last_name='Lastname',
        username='submitter', email='submitter@essolutions.se'
    )
    if created:
        user_submitter.set_password('submitter')
        user_submitter.save()
        default_org.add_member(user_submitter.essauth_member, roles=[role_submitter])

    user_deliverymgr, created = User.objects.get_or_create(
        first_name='Delivery Manager', last_name='Lastname',
        username='deliverymgr', email='deliverymgr@essolutions.se'
    )
    if created:
        user_deliverymgr.set_password('deliverymgr')
        user_deliverymgr.save()
        default_org.add_member(user_deliverymgr.essauth_member, roles=[role_delivery_manager])

    user_archivist, created = User.objects.get_or_create(
        first_name='Archivist', last_name='Lastname',
        username='archivist', email='archivist@essolutions.se'
    )
    if created:
        user_archivist.set_password('archivist')
        user_archivist.save()
        default_org.add_member(user_archivist.essauth_member, roles=[role_archivist])

    user_admin, created = User.objects.get_or_create(
        first_name='Admin', last_name='Lastname',
        username='admin', email='admin@essolutions.se',
    )
    if created:
        user_admin.set_password('admin')
        user_admin.is_staff = True
        user_admin.save()
        default_org.add_member(user_admin.essauth_member, roles=[role_administrator])

    user_sysadmin, created = User.objects.get_or_create(
        first_name='Sysadmin', last_name='Lastname',
        username='sysadmin', email='sysadmin@essolutions.se',
    )
    if created:
        user_sysadmin.set_password('sysadmin')
        user_sysadmin.is_staff = True
        user_sysadmin.save()
        default_org.add_member(user_sysadmin.essauth_member, roles=[role_system_administrator])

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

    return 0


def installDefaultPaths():
    click.echo("Installing paths...")

    dct = {
        'mimetypes_definitionfile': '/ESSArch/config/mime.types',
        'preingest': '/ESSArch/data/preingest/packages',
        'preingest_reception': '/ESSArch/data/preingest/reception',
        'ingest': '/ESSArch/data/ingest/packages',
        'ingest_reception': '/ESSArch/data/ingest/reception',
        'ingest_transfer': '/ESSArch/data/ingest/transfer',
        'ingest_unidentified': '/ESSArch/data/ingest/uip',
        'access_workarea': '/ESSArch/data/workspace',
        'ingest_workarea': '/ESSArch/data/workspace',
        'disseminations': '/ESSArch/data/disseminations',
        'orders': '/ESSArch/data/orders',
        'verify': '/ESSArch/data/verify',
        'temp': '/ESSArch/data/temp',
        'appraisal_reports': '/ESSArch/data/reports/appraisal',
        'conversion_reports': '/ESSArch/data/reports/conversion',
        'receipts': '/ESSArch/data/receipts',
    }

    for key in dct:
        print('-> %s: %s' % (key, dct[key]))
        Path.objects.get_or_create(entity=key, defaults={'value': dct[key]})

    return 0


def installDefaultStoragePolicies():
    click.echo("Installing storage policies...")

    cache_method, created_cache_method = StorageMethod.objects.get_or_create(
        name='Default Cache Storage Method',
        defaults={
            'enabled': True,
            'type': DISK,
            'containers': False,
        }
    )

    if created_cache_method:
        cache_target, created_cache_target = StorageTarget.objects.get_or_create(
            name='Default Cache Storage Target 1',
            defaults={
                'status': True,
                'type': DISK,
                'target': '/ESSArch/data/store/cache',
            }
        )

        if created_cache_target:
            StorageMedium.objects.get_or_create(
                medium_id='Default Cache Disk 1',
                defaults={
                    'storage_target': cache_target,
                    'status': 20,
                    'location': Parameter.objects.get(entity='medium_location').value,
                    'location_status': 50,
                    'block_size': cache_target.default_block_size,
                    'format': cache_target.default_format,
                    'agent': Parameter.objects.get(entity='agent_identifier_value').value,
                }
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
    click.echo("Installing storage methods...")

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
    click.echo("Installing storage targets...")
    target, created = StorageTarget.objects.get_or_create(
        name='Default Storage Target 1',
        defaults={
            'status': True,
            'type': DISK,
            'target': '/ESSArch/data/store/disk1',
        }
    )

    if created:
        StorageMedium.objects.get_or_create(
            medium_id='Default Storage Disk 1',
            defaults={
                'storage_target': target,
                'status': 20,
                'location': Parameter.objects.get(entity='medium_location').value,
                'location_status': 50,
                'block_size': target.default_block_size,
                'format': target.default_format,
                'agent': Parameter.objects.get(entity='agent_identifier_value').value,
            }
        )

    target, created = StorageTarget.objects.get_or_create(
        name='Default Long-term Storage Target 1',
        defaults={
            'status': True,
            'type': DISK,
            'target': '/ESSArch/data/store/longterm_disk1',
        }
    )

    if created:
        StorageMedium.objects.get_or_create(
            medium_id='Default Long-term Storage Disk 1',
            defaults={
                'storage_target': target,
                'status': 20,
                'location': Parameter.objects.get(entity='medium_location').value,
                'location_status': 50,
                'block_size': target.default_block_size,
                'format': target.default_format,
                'agent': Parameter.objects.get(entity='agent_identifier_value').value,
            }
        )

    return 0


def installDefaultStorageMethodTargetRelations():
    click.echo("Installing storage method target relations...")

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
    click.echo("Installing Elasticsearch pipelines...")

    conn = get_connection()
    client = IngestClient(conn)
    client.put_pipeline(id='ingest_attachment', body={
        'description': "Extract attachment information",
        'processors': [
            {
                "attachment": {
                    "field": "data",
                    "indexed_chars": "-1"
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
    click.echo("Installing search indices...")

    for _index_name, index_class in settings.ELASTICSEARCH_INDEXES['default'].items():
        doctype = locate(index_class)
        alias_migration.setup_index(doctype)

    print('done')


if __name__ == '__main__':
    installDefaultConfiguration()
