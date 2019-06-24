import errno
import logging
import os
import shutil
import tarfile

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext as _

from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.auth.models import Notification
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator, parseContent
from ESSArch_Core.ip.models import EventIP
from ESSArch_Core.ip.utils import (
    parse_submit_description_from_ip,
    generate_content_mets,
    generate_package_mets,
    generate_premis,
    generate_events_xml,
    download_schemas,
)
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.fixity.receipt import get_backend as get_receipt_backend
from ESSArch_Core.fixity.transformation import get_backend as get_transformer
from ESSArch_Core.util import (
    get_premis_ip_object_element_spec,
    normalize_path,
    zip_directory,
)

User = get_user_model()


class GenerateContentMets(DBTask):
    event_type = 50600

    def run(self):
        generate_content_mets(self.get_information_package())

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.content_mets_path)


class GeneratePackageMets(DBTask):
    event_type = 50600

    def run(self):
        generate_package_mets(self.get_information_package())

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.package_mets_path)


class GeneratePremis(DBTask):
    event_type = 50600

    def run(self):
        generate_premis(self.get_information_package())

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.get_premis_file_path())


class GenerateEventsXML(DBTask):
    event_type = 50600

    def run(self):
        generate_events_xml(self.get_information_package())

    def event_outcome_success(self):
        ip = self.get_information_package()
        return 'Generated {xml}'.format(xml=ip.get_events_file_path())


class DownloadSchemas(DBTask):
    logger = logging.getLogger('essarch.core.ip.tasks.DownloadSchemas')

    def run(self, verify=True):
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
        parse_submit_description_from_ip(self.get_information_package())

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

        backend = get_receipt_backend(backend)
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
