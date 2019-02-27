
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from ESSArch_Core.storage.exceptions import TapeDriveLockedError, RobotMountTimeoutException
from ESSArch_Core.storage.models import (
    TapeDrive,
    Robot,
    StorageMedium,
    TapeSlot,
    StorageTarget,
)
from ESSArch_Core.tasks_util import (
    unmount_tape_from_drive,
    mount_tape_medium_into_drive,
)


class TapeMountOrUnmountTests(TestCase):

    def create_tape_drive(self):
        return TapeDrive.objects.create(
            drive_id=2,
            device="unique_char",
            robot=Robot.objects.create(device="robot_device")
        )

    def create_storage_medium(self, tape_drive=None):
        robot = Robot.objects.create(device='slot_robot_device')
        tape_slot = TapeSlot.objects.create(slot_id=12, robot=robot)
        storage_target = StorageTarget.objects.create()
        return StorageMedium.objects.create(
            tape_slot=tape_slot,
            medium_id="dummy_medium_id",
            storage_target=storage_target,
            status=20,
            location="dummy_medium_location",
            location_status=50,
            block_size=512, format=103,
            agent="dummy_agent_name",
            tape_drive=tape_drive
        )

    @mock.patch('ESSArch_Core.tasks_util.unmount_tape')
    def test_unmount_success(self, mock_unmount_tape):
        mock_unmount_tape.return_value = "dummy_output"

        tape_drive = self.create_tape_drive()
        storage_medium = self.create_storage_medium(tape_drive)

        before = timezone.now()
        res = unmount_tape_from_drive(tape_drive.pk)
        after = timezone.now()

        storage_medium.refresh_from_db()
        tape_drive.refresh_from_db()

        mock_unmount_tape.assert_called_once_with("robot_device", 12, 2)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(storage_medium.tape_drive, None)
        self.assertTrue(before < tape_drive.last_change < after)
        self.assertEqual(res, "dummy_output")

    @mock.patch('ESSArch_Core.tasks_util.unmount_tape')
    def test_unmount_when_unmount_tape_raise_exception(self, mock_unmount_tape):
        mock_unmount_tape.side_effect = BaseException

        tape_drive = self.create_tape_drive()
        storage_medium = self.create_storage_medium(tape_drive)

        with self.assertRaises(BaseException):
            unmount_tape_from_drive(tape_drive.pk)

        # Refresh from DB
        storage_medium.refresh_from_db()
        storage_medium.tape_slot.refresh_from_db()
        tape_drive.refresh_from_db()

        mock_unmount_tape.assert_called_once_with("robot_device", 12, 2)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(storage_medium.status, 100)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(tape_drive.status, 100)
        self.assertEqual(storage_medium.tape_slot.status, 100)

    def test_unmount_when_drive_locked_raise_exception(self):
        tape_drive = self.create_tape_drive()
        tape_drive.locked = True
        tape_drive.save(update_fields=['locked'])
        self.create_storage_medium(tape_drive)

        with self.assertRaises(TapeDriveLockedError):
            unmount_tape_from_drive(tape_drive.pk)

    def test_unmount_when_no_medium_exists_should_raise_exception(self):
        tape_drive = self.create_tape_drive()

        with self.assertRaisesRegexp(ValueError, "No tape in tape drive to unmount"):
            unmount_tape_from_drive(tape_drive.pk)

    def test_mount_when_drive_locked_raise_exception(self):
        tape_drive = self.create_tape_drive()
        tape_drive.locked = True
        tape_drive.save(update_fields=['locked'])
        storage_medium = self.create_storage_medium(tape_drive)

        with self.assertRaises(TapeDriveLockedError):
            mount_tape_medium_into_drive(tape_drive.pk, storage_medium.pk, 120)

    @mock.patch('ESSArch_Core.tasks_util.mount_tape')
    def test_mount_when_mount_tape_raise_exception(self, mock_mount_tape):
        mock_mount_tape.side_effect = BaseException

        tape_drive = self.create_tape_drive()
        storage_medium = self.create_storage_medium(tape_drive)

        with self.assertRaises(BaseException):
            mount_tape_medium_into_drive(tape_drive.pk, storage_medium.pk, 120)

        # Refresh from DB
        storage_medium.refresh_from_db()
        storage_medium.tape_slot.refresh_from_db()
        tape_drive.refresh_from_db()

        mock_mount_tape.assert_called_once_with("robot_device", 12, 2)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(storage_medium.status, 100)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(tape_drive.status, 100)
        self.assertEqual(storage_medium.tape_slot.status, 100)

    @mock.patch('ESSArch_Core.tasks_util.wait_to_come_online')
    @mock.patch('ESSArch_Core.tasks_util.mount_tape')
    def test_mount_when_wait_to_come_online_raise_exception(self, mock_mount_tape, mock_wait_to_come_online):
        mock_wait_to_come_online.side_effect = RobotMountTimeoutException

        tape_drive = self.create_tape_drive()
        storage_medium = self.create_storage_medium(tape_drive)

        with self.assertRaises(BaseException):
            mount_tape_medium_into_drive(tape_drive.pk, storage_medium.pk, 120)

        # Refresh from DB
        storage_medium.refresh_from_db()
        storage_medium.tape_slot.refresh_from_db()
        tape_drive.refresh_from_db()

        mock_mount_tape.assert_called_once_with("robot_device", 12, 2)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(storage_medium.status, 100)
        self.assertEqual(tape_drive.locked, False)
        self.assertEqual(tape_drive.status, 100)
        self.assertEqual(storage_medium.tape_slot.status, 100)

    @mock.patch('ESSArch_Core.tasks_util.write_medium_label_to_drive')
    @mock.patch('ESSArch_Core.tasks_util.wait_to_come_online')
    @mock.patch('ESSArch_Core.tasks_util.mount_tape')
    def test_mount_success(self, mount_tape, wait_to_come_online, write_medium_label_to_drive):
        tape_drive = self.create_tape_drive()
        storage_medium = self.create_storage_medium(tape_drive)

        before = timezone.now()
        mount_tape_medium_into_drive(tape_drive.pk, storage_medium.pk, 121)
        after = timezone.now()

        # Refresh from DB
        storage_medium.refresh_from_db()
        storage_medium.tape_slot.refresh_from_db()
        tape_drive.refresh_from_db()

        mount_tape.assert_called_once_with("robot_device", 12, 2)
        wait_to_come_online.assert_called_once_with("unique_char", 121)
        self.assertEqual(tape_drive.num_of_mounts, 1)
        self.assertEqual(tape_drive.locked, True)
        self.assertTrue(before < tape_drive.last_change < after)
        self.assertEqual(storage_medium.num_of_mounts, 1)
        self.assertEqual(storage_medium.tape_drive_id, tape_drive.pk)
