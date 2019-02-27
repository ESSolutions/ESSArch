import os
import tarfile
import tempfile

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import F

from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.configuration.models import Parameter
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.essxml.util import find_files
from ESSArch_Core.fixity.format import FormatIdentifier
from ESSArch_Core.fixity.validation.backends.checksum import ChecksumValidator
from ESSArch_Core.fixity.validation.backends.format import FormatValidator
from ESSArch_Core.ip.models import InformationPackage, EventIP
from ESSArch_Core.ip.utils import get_cached_objid
from ESSArch_Core.storage.exceptions import TapeDriveLockedError
from ESSArch_Core.storage.models import StorageMedium, TapeDrive, TapeSlot
from ESSArch_Core.storage.tape import (
    unmount_tape,
    mount_tape,
    wait_to_come_online,
    tape_empty,
    create_tape_label,
    rewind_tape,
    write_to_tape,
    verify_tape_label
)
from django.utils import timezone

from ESSArch_Core.util import get_event_element_spec

User = get_user_model()


def unmount_tape_from_drive(drive):
    """
    Unmounts tape from drive into slot

    Args:
        drive: Which drive to unmount from
    """
    tape_drive = TapeDrive.objects.get(pk=drive)

    # Check if reverse one to one relation exists
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
    except BaseException:
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


def mount_tape_medium_into_drive(drive_id, medium_id, timeout):
    """
    Mounts tape into drive

    Args:
        medium_id: Which medium to mount
        drive_id: Which drive to load to
        timeout: Number of times to try to mount the tape (1 sec sleep between each retry)
    """

    medium = StorageMedium.objects.get(pk=medium_id)
    slot_id = medium.tape_slot.slot_id
    tape_drive = TapeDrive.objects.get(pk=drive_id)

    if tape_drive.locked:
        raise TapeDriveLockedError()

    tape_drive.locked = True
    tape_drive.save(update_fields=['locked'])

    try:
        mount_tape(tape_drive.robot.device, slot_id, tape_drive.drive_id)
        wait_to_come_online(tape_drive.device, timeout)
    except BaseException:
        StorageMedium.objects.filter(pk=medium_id).update(status=100)
        TapeDrive.objects.filter(pk=drive_id).update(locked=False, status=100)
        TapeSlot.objects.filter(slot_id=slot_id).update(status=100)
        raise

    TapeDrive.objects.filter(pk=drive_id).update(
        num_of_mounts=F('num_of_mounts') + 1,
        last_change=timezone.now(),
    )
    StorageMedium.objects.filter(pk=medium.pk).update(
        num_of_mounts=F('num_of_mounts') + 1,
        tape_drive_id=drive_id
    )

    write_medium_label_to_drive(drive_id, medium, slot_id, tape_drive)


def write_medium_label_to_drive(drive_id, medium, slot_id, tape_drive):
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
    except BaseException:
        StorageMedium.objects.filter(pk=medium.pk).update(status=100)
        TapeDrive.objects.filter(pk=drive_id).update(locked=False, status=100)
        TapeSlot.objects.filter(slot_id=slot_id).update(status=100)
        raise
    finally:
        xmlfile.close()
        TapeDrive.objects.filter(pk=drive_id).update(locked=False)


def validate_file_format(filename, format_name, format_registry_key, format_version):
    """
    Validates the format of the given file
    """

    fid = FormatIdentifier()
    actual_format_name, actual_format_version, actual_format_registry_key = fid.identify_file_format(filename)

    if format_name:
        assert actual_format_name == format_name, (
            "format name for %s is not valid, (%s != %s)" % filename, format_name, actual_format_name
        )

    if format_version:
        assert actual_format_version == format_version, "format version for %s is not valid" % filename

    if format_registry_key:
        assert actual_format_registry_key == format_registry_key, (
            "format registry key for %s is not valid" % filename
        )

    return "Success"


def validate_files(ip, responsible, rootdir, validate_fileformat, validate_integrity, xmlfile):
    if any([validate_fileformat, validate_integrity]):
        if rootdir is None:
            rootdir = InformationPackage.objects.values_list('object_path', flat=True).get(pk=ip)

        format_validator = FormatValidator()

        for f in find_files(xmlfile, rootdir):
            filename = os.path.join(rootdir, f.path)

            if validate_fileformat and f.format is not None:
                format_validator.validate(filename, (f.format, None, None))

            if validate_integrity and f.checksum is not None and f.checksum_type is not None:
                options = {'expected': f.checksum, 'algorithm': f.checksum_type}
                validator = ChecksumValidator(context='checksum_str', options=options)
                try:
                    validator.validate(filename)
                except Exception as e:
                    recipient = User.objects.get(pk=responsible).email
                    if recipient and ip:
                        ip = InformationPackage.objects.get(pk=ip)
                        subject = 'Rejected "%s"' % ip.object_identifier_value
                        body = '"%s" was rejected:\n%s' % (ip.object_identifier_value, str(e))
                        send_mail(subject, body, None, [recipient], fail_silently=False)

                    raise


def append_events(ip, events, filename):
    if not filename:
        ip = InformationPackage.objects.get(pk=ip)
        filename = os.path.join(ip.object_path, ip.get_events_file_path())
    generator = XMLGenerator(filepath=filename)
    template = get_event_element_spec()

    if not events:
        events = EventIP.objects.filter(linkingObjectIdentifierValue=ip)
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
            "eventType": (
                str(event.eventType.code) if event.eventType.code is not None and
                event.eventType.code != '' else str(event.eventType.eventType)),
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
