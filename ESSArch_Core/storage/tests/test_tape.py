# -*- coding: utf-8 -*-
import errno
import os
import shutil
import tarfile
import tempfile
from subprocess import PIPE
from unittest import mock

import tenacity
from django.test import TestCase
from django.utils import timezone

from ESSArch_Core.storage.exceptions import (
    MTFailedOperationException,
    MTInvalidOperationOrDeviceNameException,
    RobotException,
    RobotMountException,
    RobotMountTimeoutException,
    RobotUnmountException,
    TapeMountedError,
    TapeUnmountedError,
)


def retry_mock(*args, **kwargs):
    """
    This is a dummy decorator to override the functionalities of retrying.retry
    """
    def decorator(f):
        def decorator_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorator_function
    return decorator


tenacity.retry = retry_mock

from ESSArch_Core.storage.tape import (  # noqa isort:skip
    mount_tape,
    unmount_tape,
    rewind_tape,
    is_tape_drive_online,
    wait_to_come_online,
    tape_empty,
    create_tape_label,
    verify_tape_label,
    get_tape_file_number,
    set_tape_file_number,
    get_tape_op_and_count,
)


class TapeTests(TestCase):

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_mount_tape_non_zero_returncode(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(RobotMountException):
            mount_tape("device_to_mount", 21, 42)

        cmd = 'mtx -f device_to_mount load 21 42'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_mount_tape_non_zero_returncode_and_drive_is_full_error_msg(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'Drive 42 Full (Storage Element 21 loaded)'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(TapeMountedError):
            mount_tape("device_to_mount", 21, 42)

        cmd = 'mtx -f device_to_mount load 21 42'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_mount_tape_zero_returncode_should_return_output(self, mock_popen):
        attrs = {'communicate.return_value': ('All good', ''), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(mount_tape("device_to_mount", 21, 42), "All good")

        cmd = 'mtx -f device_to_mount load 21 42'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_unmount_tape_non_zero_returncode(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(RobotUnmountException):
            unmount_tape("device_to_unmount", 21, 42)

        cmd = 'mtx -f device_to_unmount unload 21 42'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_unmount_tape_non_zero_returncode_and_drive_is_empty_error_msg(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'Data Transfer Element 42 is Empty'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(TapeUnmountedError):
            unmount_tape("device_to_unmount", 21, 42)

        cmd = 'mtx -f device_to_unmount unload 21 42'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_unmount_tape_zero_returncode_should_return_output(self, mock_popen):
        attrs = {'communicate.return_value': ('All good', ''), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(unmount_tape("device_to_unmount", 21, 42), "All good")

        cmd = 'mtx -f device_to_unmount unload 21 42'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_rewind_tape_returncode_is_1(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(MTInvalidOperationOrDeviceNameException):
            rewind_tape("device_to_rewind")

        cmd = 'mt -f device_to_rewind rewind'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_rewind_tape_returncode_is_2(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 2}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(MTFailedOperationException):
            rewind_tape("device_to_rewind")

        cmd = 'mt -f device_to_rewind rewind'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_rewind_tape_zero_returncode_should_return_output(self, mock_popen):
        attrs = {'communicate.return_value': ('All good', ''), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(rewind_tape("device_to_rewind"), "All good")

        cmd = 'mt -f device_to_rewind rewind'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_is_tape_drive_online_non_zero_returncode(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(RobotException):
            is_tape_drive_online("device_to_verify")

        cmd = 'mt -f device_to_verify status'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_is_tape_drive_online_output_contains_ONLINE(self, mock_popen):
        attrs = {'communicate.return_value': ('the drive is ONLINE now', 'error'), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(is_tape_drive_online("device_to_verify"), True)

        cmd = 'mt -f device_to_verify status'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_is_tape_drive_online_output_not_containing_ONLINE(self, mock_popen):
        attrs = {'communicate.return_value': ('the drive is offline', 'error'), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(is_tape_drive_online("device_to_verify"), False)

        cmd = 'mt -f device_to_verify status'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.time.sleep')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online', return_value=False)
    def test_wait_to_come_online_never_get_online_should_raise_exception(self, mock_is_tape_drive_online, mock_sleep):

        with self.assertRaises(RobotMountTimeoutException):
            wait_to_come_online("device_to_wait_for", 3)

        self.assertEqual(mock_is_tape_drive_online.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 4)

    @mock.patch('ESSArch_Core.storage.tape.time.sleep')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online', return_value=False)
    def test_wait_to_come_online_default_timeout_after_121_times(self, mock_is_tape_drive_online, mock_sleep):

        with self.assertRaises(RobotMountTimeoutException):
            wait_to_come_online("device_to_wait_for")

        self.assertEqual(mock_is_tape_drive_online.call_count, 121)
        self.assertEqual(mock_sleep.call_count, 121)

    @mock.patch('ESSArch_Core.storage.tape.time.sleep')
    @mock.patch('ESSArch_Core.storage.tape.is_tape_drive_online')
    def test_wait_to_come_online_success_after_n_times_should_return(self, mock_is_tape_drive_online, mock_sleep):
        mock_is_tape_drive_online.side_effect = [False, False, True]
        wait_to_come_online("device_to_wait_for")

        self.assertEqual(mock_is_tape_drive_online.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @mock.patch('ESSArch_Core.storage.tape.tarfile')
    @mock.patch('ESSArch_Core.storage.tape.rewind_tape')
    def test_tape_empty_when_drive_not_empty(self, mock_rewind_tape, mock_tarfile):
        mocked_tar = mock.Mock()
        mock_tarfile.open.return_value = mocked_tar

        self.assertEqual(tape_empty("some_drive"), False)

        mock_tarfile.open.assert_called_once()
        mocked_tar.close.assert_called_once()
        mock_rewind_tape.assert_called_once_with("some_drive")

    @mock.patch('ESSArch_Core.storage.tape.tarfile')
    @mock.patch('ESSArch_Core.storage.tape.rewind_tape')
    def test_tape_empty_when_IO_error_then_drive_is_empty(self, mock_rewind_tape, mock_tarfile):
        exception = IOError()
        exception.errno = errno.EIO
        mock_tarfile.open.side_effect = exception

        self.assertEqual(tape_empty("some_drive"), True)

        mock_tarfile.open.assert_called_once()
        mock_rewind_tape.assert_called_once_with("some_drive")

    @mock.patch('ESSArch_Core.storage.tape.tarfile')
    def test_tape_empty_when_OSError_then_raise_exception(self, mock_tarfile):
        exception = OSError()
        mock_tarfile.open.side_effect = exception

        with self.assertRaises(OSError):
            tape_empty("some_drive")

        mock_tarfile.open.assert_called_once()

    @mock.patch('ESSArch_Core.storage.tape.tarfile.open')
    @mock.patch('ESSArch_Core.storage.tape.rewind_tape')
    def test_tape_empty_when_tarfile_ReadError_with_msg_then_drive_is_empty(self, mock_rewind_tape, mock_tarfile_open):
        exception = tarfile.ReadError()
        exception.message = 'empty file'
        mock_tarfile_open.side_effect = exception

        self.assertEqual(tape_empty("some_drive"), True)

        mock_tarfile_open.assert_called_once()
        mock_rewind_tape.assert_called_once_with("some_drive")

    @mock.patch('ESSArch_Core.storage.tape.tarfile.open')
    def test_tape_empty_when_tarfile_ReadError_and_unknown_message_then_raise_exception(self, mock_tarfile_open):
        exception = tarfile.ReadError()
        exception.message = 'some other message'
        mock_tarfile_open.side_effect = exception

        with self.assertRaises(tarfile.ReadError):
            tape_empty("some_drive")

        mock_tarfile_open.assert_called_once()

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_get_tape_file_number_returncode_is_1_raise_exception(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(MTInvalidOperationOrDeviceNameException):
            get_tape_file_number("device_to_verify")

        cmd = 'mt -f device_to_verify status | grep -i "file number"'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_get_tape_file_number_returncode_is_2_raise_exception(self, mock_popen):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 2}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(MTFailedOperationException):
            get_tape_file_number("device_to_verify")

        cmd = 'mt -f device_to_verify status | grep -i "file number"'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_get_tape_file_number_success(self, mock_popen):
        attrs = {'communicate.return_value': ('the_drive=42, something else', ''), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(get_tape_file_number("device_to_verify"), 42)

        cmd = 'mt -f device_to_verify status | grep -i "file number"'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.storage.tape.rewind_tape')
    def test_set_tape_file_number_default_should_rewind_tape(self, mock_rewind_tape):
        set_tape_file_number("device_to_update")
        mock_rewind_tape.assert_called_once_with("device_to_update")

    @mock.patch('ESSArch_Core.storage.tape.rewind_tape')
    def test_set_tape_file_number_num_is_0_should_rewind_tape(self, mock_rewind_tape):
        set_tape_file_number("device_to_update", 0)
        mock_rewind_tape.assert_called_once_with("device_to_update")

    @mock.patch('ESSArch_Core.storage.tape.get_tape_op_and_count', return_value=(43, 'someOp'))
    @mock.patch('ESSArch_Core.storage.tape.get_tape_file_number', return_value=42)
    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_set_tape_file_number_success_should_return_proc_output(self, mock_popen, mock_get_tape_fn, mock_tape_op):
        attrs = {'communicate.return_value': ('the output', ''), 'returncode': 0}
        mock_popen.return_value.configure_mock(**attrs)

        self.assertEqual(set_tape_file_number("device_to_update", 2), "the output")

        cmd = 'mt -f device_to_update someOp 43'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        mock_get_tape_fn.assert_called_once()
        mock_tape_op.assert_called_once()

    @mock.patch('ESSArch_Core.storage.tape.get_tape_op_and_count', return_value=(43, 'someOp'))
    @mock.patch('ESSArch_Core.storage.tape.get_tape_file_number', return_value=42)
    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_set_tape_file_number_returncode_is_1_raise_exception(self, mock_popen, mock_get_tape_fn, mock_tape_op):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(MTInvalidOperationOrDeviceNameException):
            set_tape_file_number("device_to_update", 3)

        cmd = 'mt -f device_to_update someOp 43'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        mock_get_tape_fn.assert_called_once()
        mock_tape_op.assert_called_once()

    @mock.patch('ESSArch_Core.storage.tape.get_tape_op_and_count', return_value=(43, 'someOp'))
    @mock.patch('ESSArch_Core.storage.tape.get_tape_file_number', return_value=42)
    @mock.patch('ESSArch_Core.storage.tape.Popen')
    def test_set_tape_file_number_returncode_is_2_raise_exception(self, mock_popen, mock_get_tape_fn, mock_tape_op):
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 2}
        mock_popen.return_value.configure_mock(**attrs)

        with self.assertRaises(MTFailedOperationException):
            set_tape_file_number("device_to_update", 3)

        cmd = 'mt -f device_to_update someOp 43'
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)
        mock_get_tape_fn.assert_called_once()
        mock_tape_op.assert_called_once()

    def test_get_tape_op_and_count(self):
        self.assertEqual(get_tape_op_and_count(42, 32), (11, 'bsfm'))
        self.assertEqual(get_tape_op_and_count(52, 32), (21, 'bsfm'))

        self.assertEqual(get_tape_op_and_count(32, 42), (10, 'fsf'))
        self.assertEqual(get_tape_op_and_count(32, 62), (30, 'fsf'))

        self.assertEqual(get_tape_op_and_count(42, 42), (1, 'bsfm'))
        self.assertEqual(get_tape_op_and_count(52, 52), (1, 'bsfm'))


class TapeLabelTest(TestCase):

    def setUp(self):
        self.bd = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bd)
        self.datadir = os.path.join(self.bd, "datadir")
        os.makedirs(self.datadir)

    def get_mocked_medium(self, m_id, m_date, m_format, m_block_size, m_type):
        mock_medium = mock.MagicMock()

        mock_medium.medium_id = m_id
        mock_medium.create_date = m_date
        mock_medium.storage_target.default_format = m_format
        mock_medium.storage_target.default_block_size = m_block_size
        mock_medium.storage_target.type = m_type

        return mock_medium

    def get_valid_xml_with_date(self, m_id, m_date, m_format, m_block_size, m_type):
        converted_time = timezone.localtime(m_date).replace(microsecond=0).isoformat()
        return f"""\
<?xml version='1.0' encoding='UTF-8'?>
<label>
  <tape id="{m_id}" date="{converted_time}"/>
  <format format="{m_format}" blocksize="{m_block_size}" drivemanufacture="{m_type}"/>
</label>
"""

    def test_create_tape_label_validate_xml(self):
        current_time = timezone.now()
        mock_medium = self.get_mocked_medium("code id", current_time, 103, 512, 325)
        xml_content = self.get_valid_xml_with_date("code id", current_time, 103, 512, 325)

        xmlpath = os.path.join(self.datadir, "tape_label.xml")

        create_tape_label(mock_medium, xmlpath)

        with open(xmlpath, 'r') as f:
            file_content = f.read()
            self.assertEqual(xml_content, file_content)

    def test_verify_tape_label_success_should_return_True(self):
        current_time = timezone.now()
        mock_medium = self.get_mocked_medium("code id", current_time, 103, 512, 325)
        xml_content = self.get_valid_xml_with_date("code id", current_time, 103, 512, 325)

        self.assertEqual(verify_tape_label(mock_medium, xml_content.encode()), True)

    def test_verify_tape_label_bad_xml_should_return_False(self):
        current_time = timezone.now()
        mock_medium = self.get_mocked_medium("code id", current_time, 103, 512, 325)
        xml_content = """badXML"""

        self.assertEqual(verify_tape_label(mock_medium, xml_content.encode()), False)

    def test_verify_tape_label_id_differs_should_return_False(self):
        current_time = timezone.now()
        mock_medium = self.get_mocked_medium("code id", current_time, 103, 512, 325)
        xml_content = self.get_valid_xml_with_date("some other id", current_time, 103, 512, 325)

        self.assertEqual(verify_tape_label(mock_medium, xml_content.encode()), False)

    def test_verify_tape_label_tape_tag_missing_should_return_False(self):
        current_time = timezone.now()
        mock_medium = self.get_mocked_medium("code id", current_time, 103, 512, 325)
        xml_content = f"""\
<?xml version='1.0' encoding='UTF-8'?>
<label>
  <format format="103" blocksize="512" drivemanufacture="325"/>
</label>
"""

        self.assertEqual(verify_tape_label(mock_medium, xml_content.encode()), False)
