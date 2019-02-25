import errno
import logging
import os
import shutil
import tarfile

import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext as _
from lxml import etree

from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.auth.models import Notification
from ESSArch_Core.configuration.models import ArchivePolicy, Path
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator, parseContent
from ESSArch_Core.essxml.util import get_agents, parse_submit_description
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import Agent, EventIP, InformationPackage, MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.fixity.receipt import get_backend as get_receipt_backend
from ESSArch_Core.fixity.transformation import get_backend as get_transformer
from ESSArch_Core.util import (creation_date, find_destination, get_event_spec,
                               get_premis_ip_object_element_spec, normalize_path,
                               timestamp_to_datetime, zip_directory)

User = get_user_model()


class GenerateContentMets(DBTask):
    event_type = 50600

    def run(self):
        ip = self.get_information_package()
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

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.content_mets_path)


class GeneratePackageMets(DBTask):
    event_type = 50600

    def run(self):
        ip = self.get_information_package()
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

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.package_mets_path)


class GeneratePremis(DBTask):
    event_type = 50600

    def run(self):
        ip = self.get_information_package()
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

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.get_premis_file_path())


class GenerateEventsXML(DBTask):
    event_type = 50600

    def run(self):
        ip = self.get_information_package()
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

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.get_events_file_path())


class DownloadSchemas(DBTask):
    logger = logging.getLogger('essarch.core.ip.tasks.DownloadSchemas')

    def run(self, verify=True):
        ip = self.get_information_package()
        ip_profile_type = ip.get_package_type_display().lower()
        ip_profile = ip.get_profile_rel(ip_profile_type).profile
        structure = ip.get_structure()
        rootdir = ip.object_path

        specifications = [ip_profile.specification, get_event_spec()]
        premis_profile_rel = ip.get_profile_rel('preservation_metadata')
        if premis_profile_rel is not None:
            specifications.append(premis_profile_rel.profile.specification)

        self.logger.debug(u'Downloading schemas')
        for spec in specifications:
            schema_preserve_loc = spec.get('-schemaPreservationLocation', 'xsd_files')
            if schema_preserve_loc and structure:
                reldir, _ = find_destination(schema_preserve_loc, structure)
                dirname = os.path.join(rootdir, reldir)
            else:
                dirname = rootdir

            for schema in spec.get('-schemasToPreserve', []):
                dst = os.path.join(dirname, os.path.basename(schema))
                self.logger.info(u'Downloading schema from {} to {}'.format(schema, dst))
                try:
                    r = requests.get(schema, stream=True, verify=verify)
                    r.raise_for_status()
                    with open(dst, 'wb') as f:
                        for chunk in r:
                            f.write(chunk)
                except Exception:
                    self.logger.exception(u'Download of schema failed: {}'.format(schema))
                    try:
                        self.logger.debug(u'Deleting downloaded file if it exists: {}'.format(dst))
                        os.remove(dst)
                    except OSError as e:
                        if e.errno != errno.ENOENT:
                            self.logger.exception(u'Failed to delete downloaded file: {}'.format(dst))
                            raise
                    else:
                        self.logger.info(u'Deleted downloaded file: {}'.format(dst))
                    raise
                else:
                    self.logger.info(u'Downloaded schema to {}'.format(dst))
        else:
            self.logger.info(u'No schemas to download')


class AddPremisIPObjectElementToEventsFile(DBTask):
    def run(self):
        ip = self.get_information_package()
        info = {
            'FIDType': "UUID",
            'FID': ip.object_identifier_value,
            'FFormatName': ip.get_container_format().upper(),
            'FLocationType': 'URI',
            'FName': ip.object_path,
        }
        spec = get_premis_ip_object_element_spec()
        info = fill_specification_data(info, ip=ip)
        xmlfile = os.path.join(ip.object_path, ip.get_events_file_path())

        generator = XMLGenerator(filepath=xmlfile)
        target = generator.find_element('premis')
        generator.insert_from_specification(target, spec, data=info, index=0)
        generator.write(xmlfile)


class CreatePhysicalModel(DBTask):
    event_type = 10300

    def get_dirs(self, structure, data, root=""):
        for content in structure:
            if content.get('type') == 'folder':
                name = content.get('name')
                dirname = os.path.join(root, name)
                dirname = parseContent(dirname, data)
                if not content.get('create', True):
                    continue

                yield dirname
                for x in self.get_dirs(content.get('children', []), data, dirname):
                    yield x

    def run(self, structure=None, root=""):
        """
        Creates the IP physical model based on a logical model.

        Args:
            structure: A dict specifying the logical model.
            root: The root directory to be used
        """

        ip = self.get_information_package()
        data = fill_specification_data(ip=ip, sa=ip.submission_agreement)
        structure = structure or ip.get_structure()
        root = ip.object_path if not root else root

        created = []
        try:
            for dirname in self.get_dirs(structure, data, root):
                try:
                    os.makedirs(dirname)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                created.append(dirname)
        except Exception:
            for dirname in created:
                try:
                    shutil.rmtree(dirname)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
            raise

        self.set_progress(1, total=1)

    def event_outcome_success(self, *args, **kwargs):
        return "Created physical model for %s" % self.ip_objid


class CreateContainer(DBTask):
    def run(self):
        ip = self.get_information_package()
        container_format = ip.get_container_format().lower()
        tpp = ip.get_profile_rel('transfer_project').profile
        compress = tpp.specification_data.get('container_format_compression', False)

        src = ip.object_path
        dst_dir = Path.objects.cached('entity', 'path_preingest_reception', 'value')
        dst_filename = ip.object_identifier_value + '.' + container_format
        dst = normalize_path(os.path.join(dst_dir, dst_filename))

        if container_format == 'zip':
            self.event_type = 50410
            zip_directory(dirname=src, zipname=dst, compress=compress)
        else:
            self.event_type = 50400
            compression = ':gz' if compress else ''
            base_dir = os.path.basename(os.path.normpath(ip.object_path))
            with tarfile.open(dst, 'w%s' % compression) as new_tar:
                new_tar.add(src, base_dir)

        ip.object_path = dst
        ip.save()
        shutil.rmtree(src)
        return dst

    def event_outcome_success(self):
        ip = self.get_information_package()
        return "Created {path}".format(path=ip.object_path)


class ParseSubmitDescription(DBTask):
    @transaction.atomic
    def run(self):
        ip = self.get_information_package()
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

        for agent_el in get_agents(etree.parse(xml)):
            agent = Agent.objects.from_mets_element(agent_el)
            ip.agents.add(agent)

        ip.save()

    def event_outcome_success(self):
        ip = self.get_information_package()
        return "Parsed submit description at {}".format(ip.package_mets_path)


class ParseEvents(DBTask):
    event_type = 50630

    def get_path(self, ip):
        return ip.get_events_file_path(from_container=True)

    @transaction.atomic
    def run(self):
        ip = self.get_information_package()
        xmlfile = ip.open_file(self.get_path(ip), 'rb')
        events = EventIP.objects.from_premis_file(xmlfile, save=False)
        EventIP.objects.bulk_create(events, 100)

    def event_outcome_success(self):
        ip = self.get_information_package()
        return "Parsed events from %s" % self.get_path(ip)


class Transform(DBTask):
    def run(self, backend, path=None):
        ip = self.get_information_package()
        user = User.objects.filter(pk=self.responsible).first()
        backend = get_transformer(backend, ip, user)
        if path is None and ip is not None:
            path = ip.object_path
        backend.transform(path)


class CreateReceipt(DBTask):
    def run(self, task, backend, template, destination, outcome, short_message, message, date=None):
        ip = self.get_information_package()
        template, destination, outcome, short_message, message, date = self.parse_params(
            template, destination, outcome, short_message, message, date
        )
        if date is None:
            date = timezone.now()

        backend = get_receipt_backend(backend, ip)
        if task is None:
            task = self.task_id
        backend.create(template, destination, outcome, short_message, message, date, ip=ip, task=task)


class DeleteInformationPackage(DBTask):
    def run(self, from_db=False):
        ip = self.get_information_package()
        ip.delete_workareas()
        ip.delete_files()

        if from_db:
            ip.delete()
        else:
            ip.state = 'deleted'
            ip.save()

        Notification.objects.create(message=_('%(ip)s has been deleted') % {'ip': ip.object_identifier_value},
                                    level=logging.INFO, user_id=self.responsible, refresh=True)
