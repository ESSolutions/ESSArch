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

import logging
import os
import shutil
import tarfile
from os import walk
from pathlib import PurePath

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext
from django_redis import get_redis_connection
from lxml import etree
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential,
)

from ESSArch_Core.auth.models import Notification
from ESSArch_Core.config.celery import app
from ESSArch_Core.crypto import decrypt_remote_credentials
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.essxml.util import find_pointers, get_premis_ref
from ESSArch_Core.fixity import validation
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.transformation import get_backend as get_transformer
from ESSArch_Core.fixity.validation.backends.xml import (
    DiffCheckValidator,
    XMLComparisonValidator,
    XMLSchemaValidator,
)
from ESSArch_Core.ip.models import InformationPackage, Workarea
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.storage.copy import DEFAULT_BLOCK_SIZE, copy_dir, copy_file
from ESSArch_Core.storage.exceptions import NoSpaceLeftError
from ESSArch_Core.storage.models import TapeDrive
from ESSArch_Core.storage.tape import (
    DEFAULT_TAPE_BLOCK_SIZE,
    get_tape_file_number,
    is_tape_drive_online,
    read_tape,
    rewind_tape,
    robot_inventory,
    set_tape_file_number,
    write_to_tape,
)
from ESSArch_Core.tasks_util import (
    append_events,
    mount_tape_medium_into_drive,
    unmount_tape_from_drive,
    validate_file_format,
    validate_files,
)
from ESSArch_Core.util import (
    convert_file,
    delete_path,
    find_destination,
    get_tree_size_and_count,
    zip_directory,
)
from ESSArch_Core.WorkflowEngine.polling import get_backend
from ESSArch_Core.WorkflowEngine.util import create_workflow

User = get_user_model()
redis = get_redis_connection()


@app.task(bind=True)
def Notify(self, message, level, refresh, recipient=None):
    message, = self.parse_params(message)
    if recipient is None:
        recipient = User.objects.get(pk=self.responsible)

    Notification.objects.create(
        message=message,
        level=level,
        user=recipient,
        refresh=refresh
    )


@app.task(bind=True, event_type=50600)
def GenerateXML(self, filesToCreate=None, folderToParse=None, extra_paths_to_parse=None,
                parsed_files=None, algorithm='SHA-256'):
    """
    Generates the XML using the specified data and folder, and adds the XML
    to the specified files
    """

    if filesToCreate is None:
        filesToCreate = {}

    if extra_paths_to_parse is None:
        extra_paths_to_parse = []

    if parsed_files is None:
        parsed_files = []

    ip = InformationPackage.objects.filter(pk=self.ip).first()
    sa = None
    allow_unknown_file_types = False
    allow_encrypted_files = False
    if ip is not None:
        sa = ip.submission_agreement
        allow_unknown_file_types = ip.get_allow_unknown_file_types()
        allow_encrypted_files = ip.get_allow_encrypted_files()

    for _, v in filesToCreate.items():
        v['data'] = fill_specification_data(v['data'], ip=ip, sa=sa)

    generator = XMLGenerator(
        allow_unknown_file_types=allow_unknown_file_types,
        allow_encrypted_files=allow_encrypted_files,
    )
    generator.generate(
        filesToCreate, folderToParse=folderToParse, extra_paths_to_parse=extra_paths_to_parse,
        parsed_files=parsed_files, algorithm=algorithm,
    )

    if filesToCreate is None:
        filesToCreate = {}
    msg = "Generated %s" % ", ".join(filesToCreate.keys())
    self.create_success_event(msg)


@app.task(bind=True)
def InsertXML(self, filename=None, elementToAppendTo=None, spec=None, info=None, index=None):
    """
    Inserts XML to the specifed file
    """
    if spec is None:
        spec = {}

    if info is None:
        info = {}

    generator = XMLGenerator(filepath=filename)
    target = generator.find_element(elementToAppendTo)
    generator.insert_from_specification(target, spec, data=info, index=index)
    generator.write(filename)

    msg = "Inserted XML to element %s in %s" % (elementToAppendTo, filename)
    self.create_success_event(msg)


@app.task(bind=True, event_type=50610)
def AppendEvents(self, filename="", events=None):
    append_events(self.ip, events, filename)

    if not filename:
        ip = InformationPackage.objects.get(pk=self.ip)
        filename = ip.get_events_file_path()
    msg = "Appended events to %s" % filename
    self.create_success_event(msg)


@app.task(bind=True, event_type=50400)
def CreateTAR(self, dirname=None, tarname=None, compress=False):
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
        new_tar.format = settings.TARFILE_FORMAT
        new_tar.add(dirname, base_dir)

    self.set_progress(100, total=100)
    msg = "Created %s from %s" % (tarname, dirname)
    self.create_success_event(msg)
    return tarname


@app.task(bind=True)
def ExtractTAR(self, path, dst, compression=False):
    compression = ':gz' if compression else ''
    with tarfile.open(path, 'r%s' % compression) as tar:
        tar.extractall(dst)

    self.set_progress(100, total=100)
    return dst


@app.task(bind=True, event_type=50410)
def CreateZIP(self, dirname=None, zipname=None, compress=False):
    """
    Creates a ZIP file from the specified directory

    Args:
        dirname: The directory to create a ZIP from
        zipname: The name of the zip file
        compress: Compresses the zip file if true
    """

    zip_directory(dirname, zipname, compress)

    self.set_progress(100, total=100)
    msg = "Created %s from %s" % (zipname, dirname)
    self.create_success_event(msg)
    return zipname


@app.task(bind=True)
def ValidateFiles(self, ip=None, xmlfile=None, validate_fileformat=True, validate_integrity=True, rootdir=None):
    validate_files(self.ip, self.responsible, rootdir, validate_fileformat, validate_integrity, xmlfile)

    msg = "Validated files in %s" % xmlfile
    self.create_success_event(msg)


@app.task(bind=True, queue='validation')
def ValidateFileFormat(self, filename=None, format_name=None, format_version=None, format_registry_key=None):
    res = validate_file_format(filename, format_name, format_registry_key, format_version)

    msg = "Validated format of %s to be: format name: %s, format version: %s, format registry key: %s" % (
        filename, format_name, format_version, format_registry_key
    )
    self.create_success_event(msg)
    return res


@app.task(bind=True, queue='validation')
def ValidateWorkarea(self, workarea, validators, stop_at_failure=True):
    def create_notification(ip):
        errcount = Validation.objects.filter(information_package=ip, passed=False, required=True).count()

        if errcount:
            Notification.objects.create(
                message=gettext('Validation of "{ip}" failed with {errcount} error(s)').format(
                    ip=ip, errcount=errcount
                ),
                level=logging.ERROR,
                user_id=self.responsible,
                refresh=True
            )
        else:
            Notification.objects.create(
                message=gettext('"{ip}" was successfully validated').format(
                    ip=ip
                ),
                level=logging.INFO,
                user_id=self.responsible,
                refresh=True
            )

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
                                 task=self.get_processtask(), stop_at_failure=stop_at_failure,
                                 responsible=responsible)
    except ValidationError:
        create_notification(ip)
    else:
        create_notification(ip)
    finally:
        validations = ip.validation_set.all()
        failed_validators = validations.values('validator').filter(
            passed=False, required=True
        ).values_list('validator', flat=True)

        for k, _v in workarea.successfully_validated.items():
            class_name = validation.AVAILABLE_VALIDATORS[k].split('.')[-1]
            workarea.successfully_validated[k] = class_name not in failed_validators

        workarea.save(update_fields=['successfully_validated'])


@app.task(bind=True)
def TransformWorkarea(self, backend, workarea):
    workarea = Workarea.objects.select_related('ip__submission_agreement').get(pk=workarea)
    ip = workarea.ip
    user = User.objects.filter(pk=self.responsible).first()
    backend = get_transformer(backend, ip, user)
    backend.transform(workarea.path)


@app.task(bind=True, queue='validation', event_type=50210)
def ValidateXMLFile(self, xml_filename=None, schema_filename=None, rootdir=None):
    """
    Validates (using LXML) an XML file using a specified schema file
    """

    Validation.objects.filter(task=self.get_processtask()).delete()
    xml_filename, schema_filename = self.parse_params(xml_filename, schema_filename)
    if rootdir is None and self.ip is not None:
        ip = InformationPackage.objects.get(pk=self.ip)
        rootdir = ip.object_path
    else:
        rootdir, = self.parse_params(rootdir)

    validator = XMLSchemaValidator(
        context=schema_filename,
        options={'rootdir': rootdir},
        ip=self.ip,
        task=self.get_processtask()
    )
    validator.validate(xml_filename)

    msg = "Validated %s against schema" % xml_filename
    self.create_success_event(msg)
    return "Success"


@app.task(bind=True, queue='validation', event_type=50220)
def ValidateLogicalPhysicalRepresentation(self, path, xmlfile, skip_files=None, relpath=None):
    """
    Validates the logical and physical representation of objects.
    """

    Validation.objects.filter(task=self.get_processtask()).delete()
    path, xmlfile, = self.parse_params(path, xmlfile)
    if skip_files is None:
        skip_files = []
    else:
        skip_files = self.parse_params(*skip_files)

    if relpath is not None:
        rootdir, = self.parse_params(relpath) or path
    else:
        if os.path.isdir(path):
            rootdir = path
        else:
            rootdir = os.path.dirname(path)

    ip = InformationPackage.objects.get(pk=self.ip)
    validator = DiffCheckValidator(context=xmlfile, exclude=skip_files, options={'rootdir': rootdir},
                                   task=self.get_processtask(), ip=self.ip, responsible=ip.responsible)
    msg = validator.validate(path)

    self.create_success_event(msg)
    return msg


@app.task(bind=True, queue='validation', event_type=50240)
def CompareXMLFiles(self, first, second, rootdir=None, recursive=True):
    Validation.objects.filter(task=self.get_processtask()).delete()
    first, second = self.parse_params(first, second)
    ip = InformationPackage.objects.get(pk=self.ip)
    if rootdir is None:
        rootdir = ip.object_path
    else:
        rootdir, = self.parse_params(rootdir)

    validator = XMLComparisonValidator(
        context=first,
        options={'rootdir': rootdir, 'recursive': recursive},
        task=self.get_processtask(),
        ip=self.ip,
        responsible=ip.responsible,
    )
    validator.validate(second)

    msg = "%s and %s has the same set of files" % (first, second)
    self.create_success_event(msg)


@app.task(bind=True, queue='validation', event_type=50240)
def CompareRepresentationXMLFiles(self):
    Validation.objects.filter(task=self.get_processtask()).delete()
    ip = InformationPackage.objects.get(pk=self.ip)

    reps_path, reps_dir = find_destination("representations", ip.get_structure(), ip.object_path)
    if reps_path is None:
        return None

    representations_dir = os.path.join(reps_path, reps_dir)

    for p in find_pointers(os.path.join(ip.object_path, ip.content_mets_path)):
        rep_mets_path = p.path
        rep_mets_path = os.path.join(ip.object_path, rep_mets_path)
        rep_path = os.path.relpath(rep_mets_path, representations_dir)
        rep_path = PurePath(rep_path).parts[0]

        rep_premis_path = get_premis_ref(etree.parse(rep_mets_path)).path
        rep_premis_path = os.path.join(representations_dir, rep_path, rep_premis_path)

        validator = XMLComparisonValidator(
            context=rep_premis_path,
            options={
                'rootdir': os.path.join(representations_dir, rep_path),
                'representation': rep_path,
                'recursive': False,
            },
            task=self.get_processtask(),
            ip=self.ip,
            responsible=ip.responsible,
        )
        validator.validate(rep_mets_path)

    msg = "All XML files in the representations have the same set of files"
    self.create_success_event(msg)


@app.task(bind=True, event_type=50500)
@transaction.atomic
def UpdateIPStatus(self, status, prev=None):
    status, = self.parse_params(status)
    ip = InformationPackage.objects.get(pk=self.ip)
    if prev is None:
        t = self.get_processtask()
        t.params['prev'] = ip.state
        t.save()
    ip.state = status
    ip.save()
    ip_state_dict = {'Creating': gettext('Creating'),
                     'Created': gettext('Created'),
                     'Transforming': gettext('Transforming'),
                     'Transformed': gettext('Transformed'),
                     'Submitting': gettext('Submitting'),
                     'Submitted': gettext('Submitted'),
                     'Receiving': gettext('Receiving'),
                     'Received': gettext('Received'),
                     'Preserving': gettext('Preserving'),
                     }
    Notification.objects.create(message='{} {}'.format(
        ip_state_dict.get(status.capitalize(), status.capitalize()),
        ip,
    ),
        level=logging.INFO, user_id=self.responsible, refresh=True)

    msg = "Updated status of {} to {}".format(ip.object_identifier_value, status)
    self.create_success_event(msg)


@app.task(bind=True, event_type=50500)
@transaction.atomic
def UpdateIPPath(self, path, prev=None):
    path, = self.parse_params(path)
    if path is None:
        path = ''
    ip = InformationPackage.objects.get(pk=self.ip)
    if prev is None:
        t = self.get_processtask()
        t.params['prev'] = ip.object_path
        t.save()
    ip.object_path = path
    ip.save()

    msg = "Updated path of {} to {}".format(ip.object_identifier_value, path)
    self.create_success_event(msg)


@app.task(bind=True, queue='file_operation')
def UpdateIPSizeAndCount(self):
    ip = self.ip
    path = InformationPackage.objects.values_list('object_path', flat=True).get(pk=ip)
    size, count = get_tree_size_and_count(path)

    InformationPackage.objects.filter(pk=ip).update(
        object_size=size, object_num_items=count,
        last_changed_local=timezone.now(),
    )

    msg = "Updated size and count of IP"
    self.create_success_event(msg)

    return size, count


@app.task(bind=True, event_type=50710)
def DeleteFiles(self, path, remote_host=None, remote_credentials=None):
    path, = self.parse_params(path)
    delete_path(path, remote_host=remote_host, remote_credentials=remote_credentials, task=self.get_processtask())

    msg = "Deleted %s" % path
    self.create_success_event(msg)


@app.task(bind=True)
@retry(reraise=True, retry=retry_if_exception_type(NoSpaceLeftError),
       wait=wait_exponential(max=60), stop=stop_after_delay(600))
def CopyDir(self, src, dst, remote_credentials=None, block_size=DEFAULT_BLOCK_SIZE):
    src, dst = self.parse_params(src, dst)
    requests_session = None
    if remote_credentials:
        user, passw = decrypt_remote_credentials(remote_credentials)
        requests_session = requests.Session()
        requests_session.verify = settings.REQUESTS_VERIFY
        requests_session.auth = (user, passw)

    copy_dir(src, dst, requests_session=requests_session, block_size=block_size)

    msg = "Copied %s to %s" % (src, dst)
    self.create_success_event(msg)


@app.task(bind=True)
def MoveDir(self, src, dst):
    src, dst = self.parse_params(src, dst)
    shutil.move(src, dst)

    msg = "Moved %s to %s" % (src, dst)
    self.create_success_event(msg)


@app.task(bind=True)
@retry(reraise=True, retry=retry_if_exception_type(NoSpaceLeftError),
       wait=wait_exponential(max=60), stop=stop_after_delay(600))
def CopyFile(self, src, dst, remote_credentials=None, block_size=DEFAULT_BLOCK_SIZE):
    """
    Copies the given file to the given destination

    Args:
        src: The file to copy
        dst: Where the file should be copied to
        remote_credentials: Credentials for remote server
        block_size: Size of each block to copy
    Returns:
        None
    """

    src, dst = self.parse_params(src, dst)
    requests_session = None
    if remote_credentials:
        user, passw = decrypt_remote_credentials(remote_credentials)
        requests_session = requests.Session()
        requests_session.verify = settings.REQUESTS_VERIFY
        requests_session.auth = (user, passw)

    copy_file(src, dst, requests_session=requests_session, block_size=block_size)

    msg = "Copied %s to %s" % (src, dst)
    self.create_success_event(msg)


@app.task(bind=True)
def SendEmail(self, sender=None, recipients=None, subject=None, body=None, attachments=None):
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


@app.task(bind=True)
def DownloadFile(self, src=None, dst=None):
    r = requests.get(src, stream=True, verify=False)
    r.raise_for_status()
    if r.status_code == 200:
        with open(dst, 'wb') as f:
            for chunk in r:
                f.write(chunk)


@app.task(bind=True, queue='io_tape', event_type=40200)
def MountTape(self, medium_id, drive_id=None, timeout=120):
    if drive_id is None:
        drive = TapeDrive.objects.filter(
            status=20, storage_medium__isnull=True, io_queue_entry__isnull=True, locked=False,
        ).order_by('num_of_mounts').first()

        if drive is None:
            raise ValueError('No tape drive available')

        drive_id = drive.pk

    mount_tape_medium_into_drive(drive_id, medium_id, timeout)


@app.task(bind=True, queue='io_tape', event_type=40100)
def UnmountTape(self, drive_id):
    return unmount_tape_from_drive(drive_id)


@app.task(bind=True)
def RewindTape(self, medium=None):
    """
    Rewinds the given tape
    """

    try:
        drive = TapeDrive.objects.get(storage_medium__pk=medium)
    except TapeDrive.DoesNotExist:
        raise ValueError("Tape not mounted")

    return rewind_tape(drive.device)


@app.task(bind=True)
def IsTapeDriveOnline(self, drive=None):
    """
    Checks if the given tape drive is online

    Args:
        drive: Which drive to check

    Returns:
        True if the drive is online, false otherwise
    """

    return is_tape_drive_online(drive)


@app.task(bind=True)
def ReadTape(self, medium=None, path='.', block_size=DEFAULT_TAPE_BLOCK_SIZE):
    """
    Reads the tape in the given drive
    """

    try:
        drive = TapeDrive.objects.get(storage_medium__pk=medium)
    except TapeDrive.DoesNotExist:
        raise ValueError("Tape not mounted")

    read_tape(drive.device, path=path, block_size=block_size)

    drive.last_change = timezone.now()
    drive.save(update_fields=['last_change'])

    return None


@app.task(bind=True)
def WriteToTape(self, medium, path, block_size=DEFAULT_TAPE_BLOCK_SIZE):
    """
    Writes content to a tape drive
    """

    try:
        drive = TapeDrive.objects.get(storage_medium__pk=medium)
    except TapeDrive.DoesNotExist:
        raise ValueError("Tape not mounted")

    write_to_tape(drive.device, path, block_size=block_size)

    drive.last_change = timezone.now()
    drive.save(update_fields=['last_change'])

    return None


@app.task(bind=True)
def GetTapeFileNumber(self, medium=None):
    """
    Gets the current file number (position) of the given tape
    """

    try:
        drive = TapeDrive.objects.get(storage_medium__pk=medium)
    except TapeDrive.DoesNotExist:
        raise ValueError("Tape not mounted")

    return get_tape_file_number(drive.device)


@app.task(bind=True)
def SetTapeFileNumber(self, medium=None, num=0):
    """
    Sets the current file number (position) of the given tape
    """

    try:
        drive = TapeDrive.objects.get(storage_medium__pk=medium)
    except TapeDrive.DoesNotExist:
        raise ValueError("Tape not mounted")

    return set_tape_file_number(drive.device, num)


@app.task(bind=True, queue='robot')
def RobotInventory(self, robot):
    """
    Updates the slots and drives in the robot

    Args:
        robot: Which robot to get the data from

    Returns:
        None
    """

    robot_inventory(robot)


@app.task(bind=True, event_type=50750)
def ConvertFile(self, path, format_map, delete_original=True):
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

    for root, _dirs, filenames in walk(path):
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

    msg = "Converted %s file(s) at %s" % (self.files_count, path,)
    self.create_success_event(msg)


@app.task(bind=True)
@transaction.atomic
def RunWorkflowPollers(self):
    def get_workflows():
        pollers = getattr(settings, 'ESSARCH_WORKFLOW_POLLERS', {})
        for name, poller in pollers.items():
            backend = get_backend(name)
            poll_path = poller['path']
            poll_sa = poller.get('sa')
            context = {
                'WORKFLOW_POLLER': name,
                'WORKFLOW_POLL_PATH': poll_path
            }
            for ip in backend.poll(poll_path, poll_sa):
                profile = ip.submission_agreement.profile_workflow
                try:
                    spec = profile.specification
                except AttributeError:
                    if profile is None:
                        self.logger.debug('No workflow profile in SA')
                        continue
                    raise

                yield create_workflow(spec['tasks'], ip=ip, name=profile.label,
                                      on_error=spec.get('on_error'), context=context)

    self.logger = logging.getLogger('essarch.core.tasks.RunWorkflowPollers')
    for workflow in get_workflows():
        workflow.run()


@app.task(bind=True)
def DeletePollingSource(self, backend_name, poll_path):
    backend_name, poll_path = self.parse_params(backend_name, poll_path)
    backend = get_backend(backend_name)

    ip = self.get_information_package()
    backend.delete_source(poll_path, ip)
