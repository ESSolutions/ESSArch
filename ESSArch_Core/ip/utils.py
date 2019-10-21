import errno
import os

import requests
from lxml import etree
from requests import RequestException
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from ESSArch_Core.configuration.models import StoragePolicy
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.essxml.util import get_agents, parse_submit_description
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import (
    MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT,
    Agent,
    InformationPackage,
)
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.util import (
    creation_date,
    find_destination,
    get_event_spec,
    normalize_path,
    timestamp_to_datetime,
)


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
        ip.policy = StoragePolicy.objects.get(policy_id=parsed_policy)

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

    allow_unknown_file_types = ip.get_allow_unknown_file_types()
    allow_encrypted_files = ip.get_allow_encrypted_files()
    generator = XMLGenerator(
        allow_unknown_file_types=allow_unknown_file_types,
        allow_encrypted_files=allow_encrypted_files,
    )
    generator.generate(files_to_create, folderToParse=ip.object_path, algorithm=algorithm)

    ip.content_mets_path = mets_path
    ip.content_mets_create_date = timestamp_to_datetime(creation_date(mets_path)).isoformat()
    ip.content_mets_size = os.path.getsize(mets_path)
    ip.content_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
    ip.content_mets_digest = calculate_checksum(mets_path, algorithm=algorithm)
    ip.save()


def generate_package_mets(ip, package_path, xml_path):
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
    data = fill_specification_data(profile_data, ip=ip, sa=sa)
    data["_IP_CREATEDATE"] = timestamp_to_datetime(creation_date(package_path)).isoformat()
    files_to_create = {
        xml_path: {
            'spec': profile_rel.profile.specification,
            'data': data
        }
    }
    algorithm = ip.get_checksum_algorithm()

    allow_unknown_file_types = ip.get_allow_unknown_file_types()
    allow_encrypted_files = ip.get_allow_encrypted_files()
    generator = XMLGenerator(
        allow_unknown_file_types=allow_unknown_file_types,
        allow_encrypted_files=allow_encrypted_files,
    )
    generator.generate(files_to_create, folderToParse=package_path, algorithm=algorithm)

    ip.package_mets_path = normalize_path(xml_path)
    ip.package_mets_create_date = timestamp_to_datetime(creation_date(xml_path)).isoformat()
    ip.package_mets_size = os.path.getsize(xml_path)
    ip.package_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
    ip.package_mets_digest = calculate_checksum(xml_path, algorithm=algorithm)
    ip.save()


def generate_aic_mets(ip, xml_path):
    aicinfo = fill_specification_data(ip.get_profile_data('aic_description'), ip=ip.aic)
    aic_desc_profile = ip.get_profile('aic_description')
    algorithm = ip.policy.get_checksum_algorithm_display().upper()

    filesToCreate = {
        xml_path: {
            'spec': aic_desc_profile.specification,
            'data': aicinfo
        }
    }

    parsed_files = []

    for aic_ip in ip.aic.information_packages.order_by('generation'):
        parsed_files.append({
            'FName': aic_ip.object_identifier_value + '.tar',
            'FExtension': 'tar',
            'FDir': '',
            'FParentDir': '',
            'FChecksum': aic_ip.message_digest,
            'FID': str(aic_ip.pk),
            'daotype': "borndigital",
            'href': aic_ip.object_identifier_value + '.tar',
            'FMimetype': 'application/x-tar',
            'FCreated': aic_ip.create_date,
            'FFormatName': 'Tape Archive Format',
            'FFormatVersion': 'None',
            'FFormatRegistryKey': 'x-fmt/265',
            'FSize': str(aic_ip.object_size),
            'FUse': 'Datafile',
            'FChecksumType': aic_ip.get_message_digest_algorithm_display(),
            'FLoctype': 'URL',
            'FLinkType': 'simple',
            'FChecksumLib': 'ESSArch',
            'FIDType': 'UUID',
        })

    generator = XMLGenerator()
    generator.generate(filesToCreate, parsed_files=parsed_files, algorithm=algorithm)


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
    allow_unknown_file_types = ip.get_allow_unknown_file_types()
    allow_encrypted_files = ip.get_allow_encrypted_files()
    generator = XMLGenerator(
        allow_unknown_file_types=allow_unknown_file_types,
        allow_encrypted_files=allow_encrypted_files,
    )
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

    for spec in specifications:
        schema_preserve_loc = spec.get('-schemaPreservationLocation', 'xsd_files')
        if schema_preserve_loc and structure:
            reldir, _ = find_destination(schema_preserve_loc, structure)
            dirname = os.path.join(rootdir, reldir)
        else:
            dirname = rootdir

        for schema in spec.get('-schemasToPreserve', []):
            download_schema(dirname, logger, schema, verify)


@retry(retry=retry_if_exception_type(RequestException), reraise=True, stop=stop_after_attempt(5),
       wait=wait_fixed(60))
def download_schema(dirname, logger, schema, verify):
    dst = os.path.join(dirname, os.path.basename(schema))
    logger.info('Downloading schema from {} to {}'.format(schema, dst))
    try:
        r = requests.get(schema, stream=True, verify=verify)
        r.raise_for_status()
        with open(dst, 'wb') as f:
            for chunk in r:
                f.write(chunk)
    except Exception:
        logger.exception('Download of schema failed: {}'.format(schema))
        try:
            logger.debug('Deleting downloaded file if it exists: {}'.format(dst))
            os.remove(dst)
        except OSError as e:
            if e.errno != errno.ENOENT:
                logger.exception('Failed to delete downloaded file: {}'.format(dst))
                raise
        else:
            logger.info('Deleted downloaded file: {}'.format(dst))
        raise
    else:
        logger.info('Downloaded schema to {}'.format(dst))
