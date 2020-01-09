import copy
import logging
import os
import pathlib
import tarfile
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _
from groups_manager.utils import get_permission_name
from guardian.shortcuts import assign_perm

from ESSArch_Core.auth.models import GroupGenericObjects, Member, Notification
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.Generator.xmlGenerator import (
    XMLGenerator,
    parseContent,
)
from ESSArch_Core.essxml.util import parse_submit_description
from ESSArch_Core.fixity.receipt import get_backend as get_receipt_backend
from ESSArch_Core.fixity.transformation import get_backend as get_transformer
from ESSArch_Core.ip.models import EventIP, InformationPackage, Workarea
from ESSArch_Core.ip.utils import (
    download_schemas,
    generate_aic_mets,
    generate_content_mets,
    generate_events_xml,
    generate_package_mets,
    generate_premis,
    parse_submit_description_from_ip,
)
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.profiles.utils import fill_specification_data, profile_types
from ESSArch_Core.storage.copy import copy_file
from ESSArch_Core.storage.models import StorageMethod, StorageTarget
from ESSArch_Core.util import (
    delete_path,
    get_premis_ip_object_element_spec,
    normalize_path,
    zip_directory,
)
from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


class SubmitSIP(DBTask):
    event_type = 10500

    def run(self, delete_source=False, update_path=True):
        ip = InformationPackage.objects.get(pk=self.ip)

        reception = Path.objects.get(entity="ingest_reception").value
        container_format = ip.get_container_format()
        src = ip.object_path

        try:
            remote = ip.get_profile_data('transfer_project').get(
                'preservation_organization_receiver_url'
            )
        except AttributeError:
            remote = None

        session = None

        if remote:
            if update_path:
                raise ValueError('Cannot update path when submitting to remote host')

            dst, remote_user, remote_pass = remote.split(',')
            dst = urljoin(dst, 'api/ip-reception/upload/')

            session = requests.Session()
            session.verify = settings.REQUESTS_VERIFY
            session.auth = (remote_user, remote_pass)
        else:
            dst = os.path.join(reception, ip.object_identifier_value + ".%s" % container_format)

        block_size = 8 * 1000000  # 8MB
        copy_file(src, dst, requests_session=session, block_size=block_size)

        src_xml = os.path.join(os.path.dirname(src), ip.object_identifier_value + ".xml")
        if not remote:
            dst_xml = os.path.join(reception, ip.object_identifier_value + ".xml")
        else:
            dst_xml = dst
        copy_file(src_xml, dst_xml, requests_session=session, block_size=block_size)

        if update_path:
            ip.object_path = dst
            ip.package_mets_path = dst_xml
            ip.save()

        if delete_source:
            delete_path(src)
            delete_path(src_xml)

        self.set_progress(100, total=100)

    def undo(self, delete_source=False, update_path=True):
        ip = InformationPackage.objects.get(pk=self.ip)

        reception = Path.objects.get(entity="ingest_reception").value
        container_format = ip.get_container_format()

        tar = os.path.join(reception, ip.object_identifier_value + ".%s" % container_format)
        xml = os.path.join(reception, ip.object_identifier_value + ".xml")

        os.remove(tar)
        os.remove(xml)

    def event_outcome_success(self, result, *args, **kwargs):
        ip = self.get_information_package()
        return "Submitted %s" % ip.object_identifier_value


class PrepareAIP(DBTask):
    def run(self, sip_path):
        sip_path, = self.parse_params(sip_path)
        sip_path = pathlib.Path(sip_path)
        user = User.objects.get(pk=self.responsible)
        perms = copy.deepcopy(getattr(settings, 'IP_CREATION_PERMS_MAP', {}))
        organization = user.user_profile.current_organization

        object_identifier_value = sip_path.stem
        existing_sip = InformationPackage.objects.filter(
            Q(
                Q(object_path=sip_path) |
                Q(object_identifier_value=object_identifier_value),
            ),
            package_type=InformationPackage.SIP
        ).first()
        xmlfile = sip_path.with_suffix('.xml')

        if existing_sip is None:
            parsed = parse_submit_description(xmlfile.as_posix(), srcdir=sip_path.parent)
            parsed_sa = parsed.get('altrecordids', {}).get('SUBMISSIONAGREEMENT', [None])[0]

            if parsed_sa is not None:
                raise ValueError('No submission agreement found in xml')

            sa = SubmissionAgreement.objects.get(pk=parsed_sa)

            with transaction.atomic():
                ip = InformationPackage.objects.create(
                    object_identifier_value=object_identifier_value,
                    sip_objid=object_identifier_value,
                    sip_path=sip_path.as_posix(),
                    package_type=InformationPackage.AIP,
                    state='Prepared',
                    responsible=user,
                    submission_agreement=sa,
                    submission_agreement_locked=True,
                    object_path=sip_path.as_posix(),
                    package_mets_path=xmlfile.as_posix(),
                )

                member = Member.objects.get(django_user=user)
                user_perms = perms.pop('owner', [])

                organization.assign_object(ip, custom_permissions=perms)
                organization.add_object(ip)

                for perm in user_perms:
                    perm_name = get_permission_name(perm, ip)
                    assign_perm(perm_name, member.django_user, ip)

                # refresh date fields to convert them to datetime instances instead of
                # strings to allow further datetime manipulation
                ip.refresh_from_db(fields=['entry_date', 'start_date', 'end_date'])
                ip.create_profile_rels([x.lower().replace(' ', '_') for x in profile_types], user)
        else:
            with transaction.atomic():
                ip = existing_sip
                ip.sip_objid = object_identifier_value
                ip.sip_path = sip_path.as_posix()
                ip.package_type = InformationPackage.AIP
                ip.responsible = user
                ip.state = 'Prepared'
                ip.object_path = sip_path.as_posix()
                ip.package_mets_path = xmlfile.as_posix()
                ip.save()

        return str(ip.pk)


class GenerateContentMets(DBTask):
    event_type = 50600

    def run(self):
        generate_content_mets(self.get_information_package())

    def event_outcome_success(self, result, *args, **kwargs):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.content_mets_path)


class GeneratePackageMets(DBTask):
    event_type = 50600

    def run(self, package_path=None, xml_path=None):
        package_path, xml_path = self.parse_params(package_path, xml_path)
        ip = self.get_information_package()
        package_path = package_path if package_path is not None else ip.object_path
        xml_path = xml_path if xml_path is not None else os.path.splitext(package_path)[0] + '.xml'

        generate_package_mets(ip, package_path, xml_path)
        return xml_path

    def event_outcome_success(self, result, *args, **kwargs):
        return 'Generated {xml}'.format(xml=result)


class GenerateAICMets(DBTask):
    def run(self, xml_path):
        xml_path, = self.parse_params(xml_path)
        ip = self.get_information_package()
        generate_aic_mets(ip, xml_path)
        return xml_path

    def event_outcome_success(self, result, *args, **kwargs):
        return 'Generated {xml}'.format(xml=result)


class GeneratePremis(DBTask):
    event_type = 50600

    def run(self):
        generate_premis(self.get_information_package())

    def event_outcome_success(self, result, *args, **kwargs):
        ip = self.get_information_package()
        data = fill_specification_data(ip=ip)
        path = parseContent(ip.get_premis_file_path(), data)

        return 'Generated {xml}'.format(xml=path)


class GenerateEventsXML(DBTask):
    event_type = 50600

    def run(self):
        generate_events_xml(self.get_information_package())

    def event_outcome_success(self, result, *args, **kwargs):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.get_events_file_path())


class DownloadSchemas(DBTask):
    logger = logging.getLogger('essarch.core.ip.tasks.DownloadSchemas')

    def run(self, verify=settings.REQUESTS_VERIFY):
        download_schemas(self.get_information_package(), self.logger, verify)


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

    def run(self, structure=None, root=""):
        """
        Creates the IP physical model based on a logical model.

        Args:
            structure: A dict specifying the logical model.
            root: The root directory to be used
        """

        ip = self.get_information_package()
        ip.create_physical_model(structure, root)

        self.set_progress(1, total=1)

    def event_outcome_success(self, result, *args, **kwargs):
        ip = self.get_information_package()
        return "Created physical model for %s" % ip.object_identifier_value


class CreateContainer(DBTask):
    def run(self, src, dst):
        src, dst = self.parse_params(src, dst)

        ip = self.get_information_package()
        container_format = ip.get_container_format().lower()
        tpp = ip.get_profile_rel('transfer_project').profile
        compress = tpp.specification_data.get('container_format_compression', False)

        dst = normalize_path(dst)

        if os.path.isdir(dst):
            dst_filename = ip.object_identifier_value + '.' + ip.get_container_format().lower()
            dst = os.path.join(dst, dst_filename)

        if container_format == 'zip':
            self.event_type = 50410
            zip_directory(dirname=src, zipname=dst, compress=compress)
        else:
            self.event_type = 50400
            compression = ':gz' if compress else ''
            base_dir = os.path.basename(os.path.normpath(src))
            with tarfile.open(dst, 'w%s' % compression) as new_tar:
                new_tar.add(src, base_dir)

        return dst

    def event_outcome_success(self, result, src, dst):
        return "Created {}".format(dst)


class ParseSubmitDescription(DBTask):
    @transaction.atomic
    def run(self):
        parse_submit_description_from_ip(self.get_information_package())

    def event_outcome_success(self, result, *args, **kwargs):
        ip = self.get_information_package()
        return "Parsed submit description at {}".format(ip.package_mets_path)


class ParseEvents(DBTask):
    event_type = 50630
    logger = logging.getLogger('essarch.core.ip.tasks.ParseEvents')

    def get_path(self, ip):
        return ip.get_events_file_path(from_container=True)

    @transaction.atomic
    def run(self):
        ip = self.get_information_package()
        xmlfile_path = self.get_path(ip)
        try:
            xmlfile = ip.open_file(xmlfile_path, 'rb')
        except (FileNotFoundError, KeyError):
            self.logger.debug('No events file found at "{}"'.format(xmlfile_path))
            return

        events = EventIP.objects.from_premis_file(xmlfile, save=False)
        EventIP.objects.bulk_create(events, 100)

    def event_outcome_success(self, result, *args, **kwargs):
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


class PreserveInformationPackage(DBTask):
    def run(self, storage_method_pk):
        ip = self.get_information_package()
        policy = ip.policy

        if policy is None:
            raise ValueError('{} has no policy'.format(ip))

        storage_method = StorageMethod.objects.get(pk=storage_method_pk)
        policy_methods = policy.storage_methods.all()

        if storage_method not in policy_methods and storage_method != policy.cache_storage:
            raise ValueError('{} not part of {}'.format(storage_method, policy))

        try:
            storage_target = storage_method.enabled_target
        except StorageTarget.DoesNotExist:
            raise ValueError('No writeable target available for {}'.format(storage_method))

        if storage_method.containers or storage_target.remote_server:
            src = [
                ip.get_temp_container_path(),
                ip.get_temp_container_xml_path(),
                ip.get_temp_container_aic_xml_path(),
            ]
        else:
            src = [ip.object_path]

        return ip.preserve(src, storage_target, storage_method.containers, self.get_processtask())


class WriteInformationPackageToSearchIndex(DBTask):
    def run(self):
        ip = self.get_information_package()
        ip.write_to_search_index(self.get_processtask())


class CreateReceipt(DBTask):
    def run(self, task_id, backend, template, destination, outcome, short_message, message, date=None, **kwargs):
        ip = self.get_information_package()
        template, destination, outcome, short_message, message, date = self.parse_params(
            template, destination, outcome, short_message, message, date
        )
        if date is None:
            date = timezone.now()

        backend = get_receipt_backend(backend)
        if task_id is None:
            task = self.get_processtask()
        else:
            task = ProcessTask.objects.get(celery_id=task_id)
        return backend.create(template, destination, outcome, short_message, message, date, ip=ip, task=task, **kwargs)


class MarkArchived(DBTask):
    def run(self):
        ip = self.get_information_package()
        ip.archived = True
        ip.state = 'Preserved'
        ip.save()


class DeleteInformationPackage(DBTask):
    def run(self, from_db=False, delete_files=True):
        ip = self.get_information_package()

        old_state = ip.state
        ip.state = 'Deleting'
        ip.save()
        try:
            ip.delete_workareas()
            if delete_files:
                ip.delete_files()
        except BaseException:
            ip.state = old_state
            ip.save()
            raise

        self.set_progress(99, 100)

        if from_db:
            with transaction.atomic():
                ip_content_type = ContentType.objects.get_for_model(ip)
                GroupGenericObjects.objects.filter(object_id=str(ip.pk), content_type=ip_content_type).delete()
                ip.delete()
        else:
            ip.state = 'deleted'
            ip.save()

        Notification.objects.create(message=_('%(ip)s has been deleted') % {'ip': ip.object_identifier_value},
                                    level=logging.INFO, user_id=self.responsible, refresh=True)


class CreateWorkarea(DBTask):
    def run(self, ip, user, type, read_only):
        ip = InformationPackage.objects.get(pk=ip)
        user = User.objects.get(pk=user)
        Workarea.objects.create(ip=ip, user=user, type=type, read_only=read_only)
        Notification.objects.create(
            message="%s is now in workarea" % ip.object_identifier_value,
            level=logging.INFO, user=user, refresh=True
        )


class DeleteWorkarea(DBTask):
    def run(self, pk):
        Workarea.objects.filter(pk=pk).delete()
