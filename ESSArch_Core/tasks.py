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

import cPickle
import copy
import errno
import logging
import os
import shutil
import tarfile
import tempfile
import time
import zipfile

import requests
import six
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from elasticsearch import helpers as es_helpers
from elasticsearch_dsl.connections import get_connection
from lxml import etree
from redis import StrictRedis
from retrying import retry
from scandir import walk
from six.moves import urllib

from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.auth.models import Notification
from ESSArch_Core.configuration.models import Parameter, Path
from ESSArch_Core.essxml.Generator.xmlGenerator import (parseContent, XMLGenerator,
                                                        findElementWithoutNamespace)
from ESSArch_Core.essxml.util import find_files, find_pointers
from ESSArch_Core.fixity import format, transformation, validation
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator
from ESSArch_Core.fixity.validation.backends.xml import DiffCheckValidator, XMLComparisonValidator, XMLSchemaValidator
from ESSArch_Core.ip.models import EventIP, InformationPackage, Workarea
from ESSArch_Core.ip.utils import get_cached_objid
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.storage.copy import copy_file
from ESSArch_Core.storage.exceptions import TapeDriveLockedError
from ESSArch_Core.storage.models import StorageMedium, TapeDrive, TapeSlot
from ESSArch_Core.storage.tape import (DEFAULT_TAPE_BLOCK_SIZE,
                                       create_tape_label, get_tape_file_number,
                                       is_tape_drive_online, mount_tape,
                                       read_tape, rewind_tape, robot_inventory,
                                       set_tape_file_number, tape_empty,
                                       unmount_tape, verify_tape_label,
                                       wait_to_come_online, write_to_tape)
from ESSArch_Core.tags import (DELETION_PROCESS_QUEUE, DELETION_QUEUE,
                               INDEX_PROCESS_QUEUE, INDEX_QUEUE,
                               UPDATE_PROCESS_QUEUE, UPDATE_QUEUE)
from ESSArch_Core.util import (convert_file, delete_content, find_destination,
                               get_event_element_spec, get_tree_size_and_count, remove_prefix,
                               turn_off_auto_now_add, turn_on_auto_now_add,
                               win_to_posix)

User = get_user_model()
redis = StrictRedis()

class GenerateXML(DBTask):
    event_type = 50600

    def run(self, filesToCreate={}, folderToParse=None, extra_paths_to_parse=[], parsed_files=None, algorithm='SHA-256'):
        """
        Generates the XML using the specified data and folder, and adds the XML
        to the specified files
        """

        if parsed_files is None:
            parsed_files = []

        ip = InformationPackage.objects.filter(pk=self.ip).first()
        sa = None
        if ip is not None:
            sa = ip.submission_agreement

        for _, v in six.iteritems(filesToCreate):
            v['data'] = fill_specification_data(v['data'], ip=ip, sa=sa)

        generator = XMLGenerator(filesToCreate)
        generator.generate(
            folderToParse=folderToParse, extra_paths_to_parse=extra_paths_to_parse, parsed_files=parsed_files, algorithm=algorithm,
        )

    def undo(self, filesToCreate={}, folderToParse=None, extra_paths_to_parse=[], parsed_files=None, algorithm='SHA-256'):
        for f, template in six.iteritems(filesToCreate):
            try:
                os.remove(f)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise

    def event_outcome_success(self, filesToCreate={}, folderToParse=None, extra_paths_to_parse=[], parsed_files=None, algorithm='SHA-256'):
        return "Generated %s" % ", ".join(filesToCreate.keys())


class InsertXML(DBTask):
    """
    Inserts XML to the specifed file
    """

    def run(self, filename=None, elementToAppendTo=None, spec={}, info={}, index=None):
        generator = XMLGenerator(filepath=filename)
        target = generator.find_element(elementToAppendTo)
        generator.insert_from_specification(target, spec, data=info, index=index)
        generator.write(filename)

    def undo(self, filename=None, elementToAppendTo=None, spec={}, info={}, index=None):
        tree = etree.parse(filename)
        parent = findElementWithoutNamespace(tree, elementToAppendTo)

        found = parent.findall('.//{*}%s' % spec['-name'])

        if index is None or index >= len(parent):
            parent.remove(found[-1])
        else:
            parent.remove(parent[index])

        tree.write(filename, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    def event_outcome_success(self, filename=None, elementToAppendTo=None, spec={}, info={}, index=None):
        return "Inserted XML to element %s in %s" % (elementToAppendTo, filename)


class AppendEvents(DBTask):
    event_type = 50610

    def run(self, filename="", events=None):
        if not filename:
            ip = InformationPackage.objects.get(pk=self.ip)
            filename = os.path.join(ip.object_path, ip.get_events_file_path())
        generator = XMLGenerator(filepath=filename)
        template = get_event_element_spec()

        if not events:
            events = EventIP.objects.filter(linkingObjectIdentifierValue=self.ip)

        id_types = {}

        for id_type in ['event', 'linking_agent', 'linking_object']:
            entity = '%s_identifier_type' % id_type
            id_types[id_type] = Parameter.objects.cached('entity', entity, 'value')

        target = generator.find_element('premis')
        for event in events.iterator():
            objid = get_cached_objid(event.linkingObjectIdentifierValue)

            data = {
                "eventIdentifierType": id_types['event'],
                "eventIdentifierValue": str(event.eventIdentifierValue),
                "eventType": str(event.eventType.code) if event.eventType.code is not None and event.eventType.code != '' else str(event.eventType.eventType),
                "eventDateTime": str(event.eventDateTime),
                "eventDetail": event.eventType.eventDetail,
                "eventOutcome": str(event.eventOutcome),
                "eventOutcomeDetailNote": event.eventOutcomeDetailNote,
                "linkingAgentIdentifierType": id_types['linking_agent'],
                "linkingAgentIdentifierValue": event.linkingAgentIdentifierValue,
                "linkingAgentRole": event.linkingAgentRole,
                "linkingObjectIdentifierType": id_types['linking_object'],
                "linkingObjectIdentifierValue": objid,
            }

            generator.insert_from_specification(target, template, data)

        generator.write(filename)

    def event_outcome_success(self, filename="", events=None):
        if not filename:
            ip = InformationPackage.objects.get(pk=self.ip)
            filename = ip.get_events_file_path()
        return "Appended events to %s" % filename


class ParseEvents(DBTask):
    event_type = 50630

    def run(self, xmlfile, delete_file=False):
        events = EventIP.objects.from_premis_file(xmlfile, save=False)
        try:
            turn_off_auto_now_add(EventIP, 'eventDateTime')
            EventIP.objects.bulk_create(events, 100)
        finally:
            turn_on_auto_now_add(EventIP, 'eventDateTime')

        if delete_file:
            os.remove(xmlfile)


    def undo(self, xmlfile, delete_file=False):
        pass

    def event_outcome_success(self, xmlfile, delete_file=False):
        return "Parsed events from %s" % xmlfile


class CreateTAR(DBTask):
    event_type = 50400

    def run(self, dirname=None, tarname=None, compress=False):
        """
        Creates a TAR file from the specified directory

        Args:
            dirname: The directory to create a TAR from
            tarname: The name of the tar file
            compress: Compresses the tar if true
        """

        compression = ':gz' if compress else ''
        base_dir = os.path.basename(os.path.normpath(dirname))
        with tarfile.open(tarname, 'w%s' % compression) as new_tar:
            new_tar.add(dirname, base_dir)

        self.set_progress(100, total=100)
        return tarname

    def undo(self, dirname=None, tarname=None, compress=False):
        parent_dir = os.path.dirname((os.path.normpath(dirname)))

        with tarfile.open(tarname, 'r') as tar:
            tar.extractall(parent_dir)

        os.remove(tarname)

    def event_outcome_success(self, dirname=None, tarname=None, compress=False):
        return "Created %s from %s" % (tarname, dirname)


class CreateZIP(DBTask):
    event_type = 50410

    def run(self, dirname=None, zipname=None, compress=False):
        """
        Creates a ZIP file from the specified directory

        Args:
            dirname: The directory to create a ZIP from
            zipname: The name of the zip file
            compress: Compresses the zip file if true
        """

        compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
        with zipfile.ZipFile(zipname, 'w', compression) as new_zip:
            for root, dirs, files in walk(dirname):
                for d in dirs:
                    filepath = os.path.join(root, d)
                    arcname = os.path.relpath(filepath, dirname)
                    new_zip.write(filepath, arcname)
                for f in files:
                    filepath = os.path.join(root, f)
                    arcname = os.path.relpath(filepath, dirname)
                    new_zip.write(filepath, arcname)

        self.set_progress(100, total=100)
        return zipname

    def undo(self, dirname=None, zipname=None, compress=False):
        with zipfile.ZipFile(zipname, 'r') as z:
            z.extractall(dirname)

        os.remove(zipname)

    def event_outcome_success(self, dirname=None, zipname=None, compress=False):
        return "Created %s from %s" % (zipname, dirname)


class ValidateFiles(DBTask):
    def run(self, ip=None, xmlfile=None, validate_fileformat=True, validate_integrity=True, rootdir=None):
        if any([validate_fileformat, validate_integrity]):
            if rootdir is None:
                rootdir = InformationPackage.objects.values_list('object_path', flat=True).get(pk=ip)

            tasks = []
            fid = format.FormatIdentifier()

            for f in find_files(xmlfile, rootdir):
                filename = os.path.join(rootdir, f.path)

                if validate_fileformat and f.format is not None:
                    validation.validate_file_format(filename, fid, format_name=f.format)

                if validate_integrity and f.checksum is not None and f.checksum_type is not None:
                    options = {'expected': f.checksum, 'algorithm': f.checksum_type}
                    validator = ChecksumValidator(context='checksum_str', options=options)
                    try:
                        validator.validate(filename)
                    except Exception as e:
                        recipient = User.objects.get(pk=self.responsible).email
                        if recipient and self.ip:
                            ip = InformationPackage.objects.get(pk=self.ip)
                            subject = 'Rejected "%s"' % ip.object_identifier_value
                            body = '"%s" was rejected:\n%s' % (ip.object_identifier_value, str(e))
                            send_mail(subject, body, None, [recipient], fail_silently=False)

                        raise


    def undo(self, ip=None, xmlfile=None, validate_fileformat=True, validate_integrity=True, rootdir=None):
        pass

    def event_outcome_success(self, ip, xmlfile, validate_fileformat=True, validate_integrity=True, rootdir=None):
        return "Validated files in %s" % xmlfile


class ValidateFileFormat(DBTask):
    queue = 'validation'

    def run(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
        """
        Validates the format of the given file
        """

        task = ProcessTask.objects.values(
            'information_package_id', 'responsible_id'
        ).get(pk=self.request.id)

        t = ProcessTask.objects.create(
            name="ESSArch_Core.tasks.IdentifyFileFormat",
            params={
                "filename": filename,
            },
            information_package_id=task.get('information_package_id'),
            responsible_id=task.get('responsible_id'),
        )

        actual_format_name, actual_format_version, actual_format_registry_key = t.run().get()

        if format_name:
            assert actual_format_name == format_name, "format name for %s is not valid, (%s != %s)" % (filename, format_name, actual_format_name)

        if format_version:
            assert actual_format_version == format_version, "format version for %s is not valid" % filename

        if format_registry_key:
            assert actual_format_registry_key == format_registry_key, "format registry key for %s is not valid" % filename

        return "Success"

    def undo(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
        pass

    def event_outcome_success(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
        return "Validated format of %s to be: format name: %s, format version: %s, format registry key: %s" % (
            filename, format_name, format_version, format_registry_key
        )


class ValidateWorkarea(DBTask):
    queue = 'validation'

    def create_notification(self, ip):
        errcount = Validation.objects.filter(information_package=ip, passed=False, required=True).count()

        if errcount:
            Notification.objects.create(message='Validation of "{ip}" failed with {errcount} error(s)'.format(ip=ip.object_identifier_value, errcount=errcount), level=logging.ERROR, user_id=self.responsible, refresh=True)
        else:
            Notification.objects.create(message='"{ip}" was successfully validated'.format(ip=ip.object_identifier_value), level=logging.INFO, user_id=self.responsible, refresh=True)

    def run(self, workarea, validators, stop_at_failure=True):
        workarea = Workarea.objects.get(pk=workarea)
        workarea.successfully_validated = {}

        for validator in validators:
            workarea.successfully_validated[validator] = None

        workarea.save(update_fields=['successfully_validated'])
        ip = workarea.ip
        sa = ip.submission_agreement
        validation_profile = ip.get_profile('validation')
        profile_data = fill_specification_data(data=ip.get_profile_data('validation'), sa=sa, ip=ip)
        responsible = User.objects.get(pk=self.responsible)

        try:
            validation.validate_path(workarea.path, validators, validation_profile, data=profile_data, ip=ip,
                                     stop_at_failure=stop_at_failure, responsible=responsible)
        except ValidationError:
            self.create_notification(ip)
        else:
            self.create_notification(ip)
        finally:
            validations = ip.validation_set.all()
            failed_validators = validations.values('validator').filter(passed=False, required=True).values_list('validator', flat=True)

            for k, v in six.iteritems(workarea.successfully_validated):
                class_name = validation.AVAILABLE_VALIDATORS[k].split('.')[-1]
                workarea.successfully_validated[k] = class_name not in failed_validators

            workarea.save(update_fields=['successfully_validated'])


class TransformWorkarea(DBTask):
    def run(self, workarea):
        workarea = Workarea.objects.select_related('ip__submission_agreement').get(pk=workarea)
        ip = workarea.ip
        sa = ip.submission_agreement
        user = User.objects.filter(pk=self.responsible).first()
        profile = ip.get_profile('transformation')
        profile_data = fill_specification_data(data=ip.get_profile_data('transformation'), sa=sa, ip=ip)
        transformation.transform_path(workarea.path, profile, data=profile_data, ip=ip, user=user)
        return "Success"


class ValidateXMLFile(DBTask):
    event_type = 50210
    queue = 'validation'

    def run(self, xml_filename=None, schema_filename=None, rootdir=None):
        """
        Validates (using LXML) an XML file using a specified schema file
        """

        xml_filename, schema_filename = self.parse_params(xml_filename, schema_filename)
        if rootdir is None and self.ip is not None:
            ip = InformationPackage.objects.get(pk=self.ip)
            rootdir = ip.object_path
        else:
            rootdir, = self.parse_params(rootdir)

        try:
            validator = XMLSchemaValidator(context=schema_filename, options={'rootdir': rootdir})
            validator.validate(xml_filename)
        except Exception as e:
            recipient = User.objects.get(pk=self.responsible).email
            if recipient and self.ip:
                ip = InformationPackage.objects.get(pk=self.ip)
                subject = 'Rejected "%s"' % ip.object_identifier_value
                body = '"%s" was rejected:\n%s' % (ip.object_identifier_value, str(e))
                send_mail(subject, body, None, [recipient], fail_silently=False)

            raise
        return "Success"

    def undo(self, xml_filename=None, schema_filename=None, rootdir=None):
        pass

    def event_outcome_success(self, xml_filename=None, schema_filename=None, rootdir=None):
        xml_filename = self.parse_params(xml_filename)
        return "Validated %s against schema" % xml_filename


class ValidateLogicalPhysicalRepresentation(DBTask):
    """
    Validates the logical and physical representation of objects.
    """

    event_type = 50220
    queue = 'validation'

    def run(self, path, xmlfile, skip_files=None):
        path, xmlfile, = self.parse_params(path, xmlfile)
        if skip_files is None:
            skip_files = []
        else:
            skip_files = self.parse_params(*skip_files)

        if os.path.isdir(path):
            rootdir = path
        else:
            rootdir = os.path.dirname(path)

        ip = InformationPackage.objects.get(pk=self.ip)
        validator = DiffCheckValidator(context=xmlfile, exclude=skip_files, options={'rootdir': rootdir}, ip=ip,
                                       responsible=ip.responsible)
        validator.validate(path)

    def undo(self, path, xmlfile, skip_files=None):
        pass

    def event_outcome_success(self, path, xmlfile, skip_files=None):
        path, xmlfile = self.parse_params(path, xmlfile)
        return "Successfully validated logical and physical structure of {path} against {xml}".format(path=path, xml=xmlfile)


class CompareXMLFiles(DBTask):
    event_type = 50240
    queue = 'validation'

    def run(self, first, second, rootdir=None):
        first, second = self.parse_params(first, second)
        ip = InformationPackage.objects.get(pk=self.ip)
        if rootdir is None:
            rootdir = ip.object_path
        else:
            rootdir, = self.parse_params(rootdir)

        validator = XMLComparisonValidator(context=first, options={'rootdir': rootdir}, ip=ip,
                                           responsible=ip.responsible)
        validator.validate(second)

    def undo(self, first, second, rootdir=None):
        pass

    def event_outcome_success(self, first, second, rootdir=None):
        first, second = self.parse_params(first, second)
        return "%s and %s has the same set of files" % (first, second)


class UpdateIPStatus(DBTask):
    event_type = 50500

    @transaction.atomic
    def run(self, status, prev=None):
        status, = self.parse_params(status)
        ip = InformationPackage.objects.get(pk=self.ip)
        if prev is None:
            t = ProcessTask.objects.get(pk=self.task_id)
            t.params['prev'] = ip.state
            t.save()
        ip.state = status
        ip.save()
        Notification.objects.create(message='%s %s' % (status.capitalize(), ip.object_identifier_value),
                                    level=logging.INFO, user_id=self.responsible, refresh=True)

    def undo(self, status, prev=None):
        InformationPackage.objects.filter(pk=self.ip).update(state=prev)

    def event_outcome_success(self, status, prev=None):
        status, = self.parse_params(status)
        return "Updated status of %s to %s" % (get_cached_objid(str(self.ip)), status)


class UpdateIPPath(DBTask):
    event_type = 50510

    @transaction.atomic
    def run(self, path, prev=None):
        path, = self.parse_params(path)
        ip = InformationPackage.objects.get(pk=self.ip)
        if prev is None:
            t = ProcessTask.objects.get(pk=self.task_id)
            t.params['prev'] = ip.object_path
            t.save()
        ip.object_path = path
        ip.save()

    def undo(self, status, prev=None):
        InformationPackage.objects.filter(pk=self.ip).update(path=prev)

    def event_outcome_success(self, path, prev=None):
        path, = self.parse_params(path)
        return "Updated path of %s to %s" % (get_cached_objid(str(self.ip)), path)


class UpdateIPSizeAndCount(DBTask):
    queue = 'file_operation'

    def run(self):
        ip = self.ip
        path = InformationPackage.objects.values_list('object_path', flat=True).get(pk=ip)
        size, count = get_tree_size_and_count(path)

        InformationPackage.objects.filter(pk=ip).update(
            object_size=size, object_num_items=count
        )

        return size, count

    def undo(self):
        pass

    def event_outcome_success(self):
        return "Updated size and count of IP"


class DeleteFiles(DBTask):
    event_type = 50710

    def run(self, path):
        path, = self.parse_params(path)
        try:
            shutil.rmtree(path)
        except OSError as e:
            if os.name == 'nt':
                if e.errno == 267:
                    os.remove(path)
                elif e.errno != 3:
                    raise

            if e.errno == errno.ENOTDIR:
                os.remove(path)
            elif e.errno != errno.ENOENT:
                raise

    def event_outcome_success(self, path):
        return "Deleted %s" % path


class CopyDir(DBTask):
    def run(self, src, dst):
        shutil.copytree(src, dst)

    def undo(self, src, dst):
        pass

    def event_outcome_success(self, src, dst):
        return "Copied %s to %s" % (src, dst)


class CopyFile(DBTask):
    def run(self, src, dst, requests_session=None, block_size=65536):
        """
        Copies the given file to the given destination

        Args:
            src: The file to copy
            dst: Where the file should be copied to
            requests_session: The request session to be used
            block_size: Size of each block to copy
        Returns:
            None
        """

        copy_file(src, dst, requests_session=requests_session, block_size=block_size)

    def undo(self, src, dst, requests_session=None, block_size=65536):
        pass

    def event_outcome_success(self, src, dst, requests_session=None, block_size=65536):
        return "Copied %s to %s" % (src, dst)


class SendEmail(DBTask):
    def run(self, sender=None, recipients=None, subject=None, body=None, attachments=None):
        sender, subject, body = self.parse_params(sender, subject, body)
        if recipients is None:
            recipients = []
        else:
            recipients = self.parse_params(*recipients)

        if attachments is None:
            attachments = []
        else:
            attachments = self.parse_params(*attachments)

        email = EmailMessage(subject, body, sender, recipients)

        for a in attachments:
            email.attach_file(a)

        email.send()

    def undo(self, sender=None, recipients=[], subject=None, body=None, attachments=[]):
        pass

    def event_outcome_success(self, sender=None, recipients=[], subject=None, body=None, attachments=[]):
        pass


class DownloadFile(DBTask):
    def run(self, src=None, dst=None):
        r = requests.get(src, stream=True, verify=False)
        r.raise_for_status()
        if r.status_code == 200:
            with open(dst, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

    def undo(self, src=None, dst=None):
        pass

    def event_outcome_success(self, src=None, dst=None):
        pass


class MountTape(DBTask):
    event_type = 40200

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def run(self, medium=None, drive=None, timeout=120):
        """
        Mounts tape into drive

        Args:
            medium: Which medium to mount
            drive: Which drive to load to
        """

        medium = StorageMedium.objects.get(pk=medium)
        slot = medium.tape_slot.slot_id
        tape_drive = TapeDrive.objects.get(pk=drive)

        if tape_drive.locked:
            raise TapeDriveLockedError()

        tape_drive.locked = True
        tape_drive.save(update_fields=['locked'])

        try:
            mount_tape(tape_drive.robot.device, slot, tape_drive.drive_id)
            wait_to_come_online(tape_drive.device, timeout)
        except:
            StorageMedium.objects.filter(pk=medium.pk).update(status=100)
            TapeDrive.objects.filter(pk=drive).update(locked=False, status=100)
            TapeSlot.objects.filter(slot_id=slot).update(status=100)
            raise

        TapeDrive.objects.filter(pk=drive).update(
            num_of_mounts=F('num_of_mounts')+1,
            last_change=timezone.now(),
        )
        StorageMedium.objects.filter(pk=medium.pk).update(
            num_of_mounts=F('num_of_mounts')+1,
            tape_drive_id=drive
        )

        xmlfile = tempfile.NamedTemporaryFile(delete=False)

        try:
            arcname = '%s_label.xml' % medium.medium_id

            if medium.format not in [100, 101]:
                if tape_empty(tape_drive.device):
                    create_tape_label(medium, xmlfile.name)
                    rewind_tape(tape_drive.device)
                    write_to_tape(tape_drive.device, xmlfile.name, arcname=arcname)
                else:
                    tar = tarfile.open(tape_drive.device, 'r|')
                    first_member = tar.getmembers()[0]
                    tar.close()
                    rewind_tape(tape_drive.device)

                    if first_member.name.endswith('_label.xml'):
                        tar = tarfile.open(tape_drive.device, 'r|')
                        xmlstring = tar.extractfile(first_member).read()
                        tar.close()
                        if not verify_tape_label(medium, xmlstring):
                            raise ValueError('Tape contains invalid label file')
                    elif first_member.name == 'reuse':
                        create_tape_label(medium, xmlfile.name)
                        rewind_tape(tape_drive.device)
                        write_to_tape(tape_drive.device, xmlfile.name, arcname=arcname)
                    else:
                        raise ValueError('Tape contains unknown information')

                    rewind_tape(tape_drive.device)
        except:
            StorageMedium.objects.filter(pk=medium.pk).update(status=100)
            TapeDrive.objects.filter(pk=drive).update(locked=False, status=100)
            TapeSlot.objects.filter(slot_id=slot).update(status=100)
            raise
        finally:
            xmlfile.close()
            TapeDrive.objects.filter(pk=drive).update(locked=False)

    def undo(self, medium=None, drive=None, timeout=120):
        pass

    def event_outcome_success(self, medium=None, drive=None, timeout=120):
        pass


class UnmountTape(DBTask):
    event_type = 40100

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def run(self, drive=None):
        """
        Unmounts tape from drive into slot

        Args:
            drive: Which drive to unmount from
        """

        tape_drive = TapeDrive.objects.get(pk=drive)

        if not hasattr(tape_drive, 'storage_medium'):
            raise ValueError("No tape in tape drive to unmount")

        slot = tape_drive.storage_medium.tape_slot
        robot = tape_drive.robot

        if tape_drive.locked:
            raise TapeDriveLockedError()

        tape_drive.locked = True
        tape_drive.save(update_fields=['locked'])

        try:
            res = unmount_tape(robot.device, slot.slot_id, tape_drive.drive_id)
        except:
            StorageMedium.objects.filter(pk=tape_drive.storage_medium.pk).update(status=100)
            TapeDrive.objects.filter(pk=drive).update(locked=False, status=100)
            TapeSlot.objects.filter(pk=slot.pk).update(status=100)
            raise

        StorageMedium.objects.filter(pk=tape_drive.storage_medium.pk).update(
            tape_drive=None
        )

        tape_drive.last_change = timezone.now()
        tape_drive.locked = False
        tape_drive.save(update_fields=['last_change', 'locked'])

        return res


    def undo(self, robot=None, slot=None, drive=None):
        pass

    def event_outcome_success(self, robot=None, slot=None, drive=None):
        pass


class RewindTape(DBTask):
    def run(self, medium=None):
        """
        Rewinds the given tape
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return rewind_tape(drive.device)

    def undo(self, medium=None):
        pass

    def event_outcome_success(self, medium=None):
        pass


class IsTapeDriveOnline(DBTask):
    def run(self, drive=None):
        """
        Checks if the given tape drive is online

        Args:
            drive: Which drive to check

        Returns:
            True if the drive is online, false otherwise
        """

        return is_tape_drive_online(drive)

    def undo(self, drive=None):
        pass

    def event_outcome_success(self, drive=None):
        pass


class ReadTape(DBTask):
    def run(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        """
        Reads the tape in the given drive
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        res = read_tape(drive.device, path=path, block_size=block_size)

        drive.last_change = timezone.now()
        drive.save(update_fields=['last_change'])

        return res

    def undo(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass

    def event_outcome_success(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass


class WriteToTape(DBTask):
    def run(self, medium, path, block_size=DEFAULT_TAPE_BLOCK_SIZE):
        """
        Writes content to a tape drive
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        res = write_to_tape(drive.device, path, block_size=block_size)

        drive.last_change = timezone.now()
        drive.save(update_fields=['last_change'])

        return res

    def undo(self, medium, path, block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass

    def event_outcome_success(self, medium, path, block_size=DEFAULT_TAPE_BLOCK_SIZE):
        pass


class GetTapeFileNumber(DBTask):
    def run(self, medium=None):
        """
        Gets the current file number (position) of the given tape
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return get_tape_file_number(drive.device)

    def undo(self, medium=None):
        pass

    def event_outcome_success(self, medium=None):
        pass


class SetTapeFileNumber(DBTask):
    def run(self, medium=None, num=0):
        """
        Sets the current file number (position) of the given tape
        """

        try:
            drive = TapeDrive.objects.get(storage_medium__pk=medium)
        except TapeDrive.DoesNotExist:
            raise ValueError("Tape not mounted")

        return set_tape_file_number(drive.device, num)

    def undo(self, medium=None, num=0):
        pass

    def event_outcome_success(self, medium=None, num=0):
        pass


class RobotInventory(DBTask):
    def run(self, robot):
        """
        Updates the slots and drives in the robot

        Args:
            robot: Which robot to get the data from

        Returns:
            None
        """

        robot_inventory(robot)

    def undo(self, robot):
        pass

    def event_outcome_success(self, robot):
        pass


class ConvertFile(DBTask):
    event_type = 50750

    def run(self, path, format_map, delete_original=True):
        self.files_count = 0
        path, = self.parse_params(path)

        if os.path.isfile(path):
            try:
                new_format = format_map[os.path.splitext(path)[1][1:]]
            except KeyError:
                return
            else:
                convert_file(path, new_format)
                self.files_count += 1
                if delete_original:
                    os.remove(path)
            return

        for root, dirs, filenames in walk(path):
            for fname in filenames:
                filepath = os.path.join(root, fname)
                try:
                    new_format = format_map[os.path.splitext(filepath)[1][1:]]
                except KeyError:
                    continue
                else:
                    convert_file(filepath, new_format)
                    self.files_count += 1
                    if delete_original:
                        os.remove(filepath)

    def undo(self, path, format_map, delete_original=True):
        pass

    def event_outcome_success(self, path, format_map, delete_original=True):
        path, = self.parse_params(path)
        return "Converted %s file(s) at %s" % (self.files_count, path,)


class ClearTagProcessQueue(DBTask):
    _clear_process_tag_queue_lua = """
    local values = redis.call("ZREVRANGEBYSCORE", KEYS[1], ARGV[1], "-inf", "LIMIT", "0", "1000")
    if table.getn(values) > 0 then
        redis.call("RPUSH", KEYS[2], unpack(values))
        redis.call("ZREM", KEYS[1], unpack(values))
    end
    """

    _clear_process_tag_queue = redis.register_script(_clear_process_tag_queue_lua)

    def run(self):
        """
        Deletes items older than 60 seconds from the process queue
        and pushes them into their original queue
        """

        max_time = int(time.time()) - 60

        self._clear_process_tag_queue(keys=[INDEX_PROCESS_QUEUE, INDEX_QUEUE], args=[max_time])
        self._clear_process_tag_queue(keys=[UPDATE_PROCESS_QUEUE, UPDATE_QUEUE], args=[max_time])
        self._clear_process_tag_queue(keys=[DELETION_PROCESS_QUEUE, DELETION_QUEUE], args=[max_time])

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class ProcessTags(DBTask):
    id_pickles = {}
    abstract = True

    _process_tag_queue_lua = """
    local value = redis.call("RPOP", KEYS[1])
    if value then
        redis.call("ZADD", KEYS[2], ARGV[1], value)
    end
    return value"""

    _process_tag_queue = redis.register_script(_process_tag_queue_lua)

    def deserialize(self, tags):
        for tag_string in [t for t in tags if t is not None]:
            d = cPickle.loads(tag_string)
            self.id_pickles[str(d['_id'])] = tag_string
            yield d

    def run(self):
        """
        Uses a reliable queue to process the latest entries.

        Entries are popped and returned from the queue while also being added
        to the process queue. Each entry is then sent and processed by
        elasticsearch. If elasticsearch returns a successful response
        the entry is deleted from the process queue.
        """
        es = get_connection()
        tags = []
        for i in range(10000):
            epoch_time = int(time.time())
            # Pop the latest entry, add it to the process queue with the
            # current time as score and return it
            tags.append(self._process_tag_queue(keys=[self.redis_queue, self.redis_process_queue], args=[epoch_time]))

        doctypes = self.deserialize(tags)

        # Send the entries in bulk to elasticsearch
        errors = []
        for result in es_helpers.streaming_bulk(es, doctypes, raise_on_exception=False, raise_on_error=False):
            ok, info = result
            if ok:
                _id = self.get_id(info)
                tag_string = self.id_pickles[_id]
                # Delete successful entries from the process queue
                redis.zrem(self.redis_process_queue, tag_string)
            else:
                if info.get('delete', {}).get('status') == 404:
                    # trying to delete already deleted doc, delete it from
                    # the process queue
                    _id = self.get_id(info)
                    tag_string = self.id_pickles[_id]
                    redis.zrem(self.redis_process_queue, tag_string)
                else:
                    errors.append(info)

        if errors:
            raise es_helpers.BulkIndexError('%d document(s) failed to index.' % len(errors),
                                            errors)

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class IndexTags(ProcessTags):
    redis_queue = INDEX_QUEUE
    redis_process_queue = INDEX_PROCESS_QUEUE

    def deserialize(self, tags):
        for tag_string in [t for t in tags if t is not None]:
            d = cPickle.loads(tag_string).to_dict(include_meta=True)
            if d['_index'] == 'document':
                d['pipeline'] = 'ingest_attachment'
            self.id_pickles[str(d['_id'])] = tag_string
            yield d

    def get_id(self, data):
        return data['index']['_id']


class UpdateTags(ProcessTags):
    redis_queue = UPDATE_QUEUE
    redis_process_queue = UPDATE_PROCESS_QUEUE

    def get_id(self, data):
        return data['update']['_id']


class DeleteTags(ProcessTags):
    redis_queue = DELETION_QUEUE
    redis_process_queue = DELETION_PROCESS_QUEUE

    def get_id(self, data):
        return data['delete']['_id']
