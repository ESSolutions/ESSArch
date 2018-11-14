from subprocess import PIPE

import mock
from django.test import TestCase

from ESSArch_Core.util import convert_file


class ConvertFileTests(TestCase):
    @mock.patch('ESSArch_Core.util.Popen')
    def test_non_zero_returncode(self, mock_popen):
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 1}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock

        with self.assertRaises(ValueError):
            convert_file("test.docx", "pdf")

        cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % ('pdf', 'test.docx')
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.util.os.path.isfile', return_value=False)
    @mock.patch('ESSArch_Core.util.Popen')
    def test_zero_returncode_with_no_file_created(self, mock_popen, mock_isfile):
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 0}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock

        with self.assertRaises(ValueError):
            convert_file("test.docx", "pdf")

        cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % ('pdf', 'test.docx')
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)

    @mock.patch('ESSArch_Core.util.os.path.isfile', return_value=True)
    @mock.patch('ESSArch_Core.util.Popen')
    def test_zero_returncode_with_file_created(self, mock_popen, mock_isfile):
        process_mock = mock.Mock()
        attrs = {'communicate.return_value': ('output', 'error'), 'returncode': 0}
        process_mock.configure_mock(**attrs)
        mock_popen.return_value = process_mock

        self.assertEqual(convert_file("test.docx", "pdf"), 'test.pdf')

        cmd = 'unoconv -f %s -eSelectPdfVersion=1 "%s"' % ('pdf', 'test.docx')
        mock_popen.assert_called_once_with(cmd, shell=True, stderr=PIPE, stdout=PIPE)
