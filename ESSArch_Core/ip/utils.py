import errno
import os

import requests
from django.core.cache import cache
from lxml import etree

from ESSArch_Core.configuration.models import ArchivePolicy
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.essxml.util import parse_submit_description, get_agents
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import Agent, MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT, InformationPackage
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.util import timestamp_to_datetime, creation_date, normalize_path, get_event_spec, find_destination


def get_cached_objid(id):
    objid_cache_name = 'object_identifier_value_%s' % id
    objid = cache.get(objid_cache_name)

    if objid is None:
        objid = InformationPackage.objects.values_list('object_identifier_value', flat=True).get(pk=id)
        cache.set(objid_cache_name, objid, 3600 * 24)

    return objid


def get_package_type(t):
    return {
        'sip': InformationPackage.SIP,
        'aic': InformationPackage.AIC,
        'aip': InformationPackage.AIP,
        'aiu': InformationPackage.AIU,
        'dip': InformationPackage.DIP,
    }[t]


def parse_submit_description_from_ip(ip):
    rootdir = os.path.dirname(ip.object_path) if os.path.isfile(ip.object_path) else ip.object_path
    xml = ip.package_mets_path
    parsed = parse_submit_description(xml, rootdir)

    ip.label = parsed.get('label')
    ip.entry_date = parsed.get('entry_date')
    ip.start_date = parsed.get('start_date')
    ip.end_date = parsed.get('end_date')

    if ip.policy is None:
        parsed_policy = parsed.get('altrecordids', {}).get('POLICYID')[0]
        ip.policy = ArchivePolicy.objects.get(policy_id=parsed_policy)

    ip.information_class = parsed.get('information_class') or ip.policy.information_class
    if ip.information_class != ip.policy.information_class:
        raise ValueError('Information class in submit description ({}) and policy ({}) does not match'.format(
            ip.information_class, ip.policy.information_class))

    add_agents_from_xml(ip, xml)

    ip.save()


def add_agents_from_xml(ip, xml):
    for agent_el in get_agents(etree.parse(xml)):
        agent = Agent.objects.from_mets_element(agent_el)
        ip.agents.add(agent)


def generate_content_mets(ip):
    mets_path = ip.get_content_mets_file_path()
    profile_type = ip.get_package_type_display().lower()
    profile_rel = ip.get_profile_rel(profile_type)
    profile_data = ip.get_profile_data(profile_type)
    files_to_create = {
        mets_path: {
            'spec': profile_rel.profile.specification,
            'data': fill_specification_data(profile_data, ip=ip)
        }
    }
    algorithm = ip.get_checksum_algorithm()

    generator = XMLGenerator()
    generator.generate(files_to_create, folderToParse=ip.object_path, algorithm=algorithm)

    ip.content_mets_path = mets_path
    ip.content_mets_create_date = timestamp_to_datetime(creation_date(mets_path)).isoformat()
    ip.content_mets_size = os.path.getsize(mets_path)
    ip.content_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
    ip.content_mets_digest = calculate_checksum(mets_path, algorithm=algorithm)
    ip.save()


def generate_package_mets(ip):
    sa = ip.submission_agreement
    if ip.package_type == InformationPackage.SIP:
        profile_type = 'submit_description'
    elif ip.package_type == InformationPackage.AIP:
        profile_type = 'aip_description'
    else:
        raise ValueError(
            'Cannot create package mets for IP of type {package_type}'.format(
                package_type=ip.package_type
            )
        )
    profile_rel = ip.get_profile_rel(profile_type)
    profile_data = ip.get_profile_data(profile_type)
    xmlpath = os.path.splitext(ip.object_path)[0] + '.xml'
    data = fill_specification_data(profile_data, ip=ip, sa=sa)
    data["_IP_CREATEDATE"] = timestamp_to_datetime(creation_date(ip.object_path)).isoformat()
    files_to_create = {
        xmlpath: {
            'spec': profile_rel.profile.specification,
            'data': data
        }
    }
    algorithm = ip.get_checksum_algorithm()

    generator = XMLGenerator()
    generator.generate(files_to_create, folderToParse=ip.object_path, algorithm=algorithm)

    ip.package_mets_path = normalize_path(xmlpath)
    ip.package_mets_create_date = timestamp_to_datetime(creation_date(xmlpath)).isoformat()
    ip.package_mets_size = os.path.getsize(xmlpath)
    ip.package_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
    ip.package_mets_digest = calculate_checksum(xmlpath, algorithm=algorithm)
    ip.save()


def generate_premis(ip):
    premis_path = ip.get_premis_file_path()
    premis_profile_rel = ip.get_profile_rel('preservation_metadata')
    premis_profile_data = ip.get_profile_data('preservation_metadata')
    files_to_create = {
        premis_path: {
            'spec': premis_profile_rel.profile.specification,
            'data': fill_specification_data(premis_profile_data, ip=ip)
        }
    }
    algorithm = ip.get_checksum_algorithm()
    generator = XMLGenerator()
    generator.generate(files_to_create, folderToParse=ip.object_path, algorithm=algorithm)


def generate_events_xml(ip):
    xml_path = os.path.join(ip.object_path, ip.get_events_file_path())
    files_to_create = {
        xml_path: {
            'spec': get_event_spec(),
            'data': fill_specification_data(ip=ip)
        }
    }
    algorithm = ip.get_checksum_algorithm()
    generator = XMLGenerator()
    generator.generate(files_to_create, algorithm=algorithm)


def download_schemas(ip, logger, verify):
    ip_profile_type = ip.get_package_type_display().lower()
    ip_profile = ip.get_profile_rel(ip_profile_type).profile
    structure = ip.get_structure()
    rootdir = ip.object_path

    specifications = [ip_profile.specification, get_event_spec()]
    premis_profile_rel = ip.get_profile_rel('preservation_metadata')
    if premis_profile_rel is not None:
        specifications.append(premis_profile_rel.profile.specification)

    logger.debug(u'Downloading schemas')
    for spec in specifications:
        schema_preserve_loc = spec.get('-schemaPreservationLocation', 'xsd_files')
        if schema_preserve_loc and structure:
            reldir, _ = find_destination(schema_preserve_loc, structure)
            dirname = os.path.join(rootdir, reldir)
        else:
            dirname = rootdir

        for schema in spec.get('-schemasToPreserve', []):
            download_schema(dirname, logger, schema, verify)
    else:
        logger.info(u'No schemas to download')


def download_schema(dirname, logger, schema, verify):
    dst = os.path.join(dirname, os.path.basename(schema))
    logger.info(u'Downloading schema from {} to {}'.format(schema, dst))
    try:
        r = requests.get(schema, stream=True, verify=verify)
        r.raise_for_status()
        with open(dst, 'wb') as f:
            for chunk in r:
                f.write(chunk)
    except Exception:
        logger.exception(u'Download of schema failed: {}'.format(schema))
        try:
            logger.debug(u'Deleting downloaded file if it exists: {}'.format(dst))
            os.remove(dst)
        except OSError as e:
            if e.errno != errno.ENOENT:
                logger.exception(u'Failed to delete downloaded file: {}'.format(dst))
                raise
        else:
            logger.info(u'Deleted downloaded file: {}'.format(dst))
        raise
    else:
        logger.info(u'Downloaded schema to {}'.format(dst))
