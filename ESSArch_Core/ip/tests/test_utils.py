import datetime
import os
import shutil
import tempfile
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from ESSArch_Core.configuration.models import Path, StoragePolicy
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.ip.utils import (
    download_schema,
    parse_submit_description_from_ip,
)
from ESSArch_Core.profiles.models import SubmissionAgreement
from ESSArch_Core.storage.models import StorageMethod
from ESSArch_Core.util import normalize_path


class ParseSubmitDescriptionFromIpTests(TestCase):

    def setUp(self):
        self.policy = StoragePolicy.objects.create(
            policy_id="some_unique_id",
            policy_name="dummy_name",
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(entity='some other unique entity', value="some other value"),
            information_class=2,
        )
        self.sa = SubmissionAgreement.objects.create(policy=self.policy)
        self.ip = InformationPackage.objects.create()

    @mock.patch('ESSArch_Core.ip.utils.add_agents_from_xml')
    @mock.patch('ESSArch_Core.ip.utils.parse_submit_description')
    def test_parse_submit_desc_with_policy(self, mock_parse_desc, mock_agents):
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)

        mock_parse_desc.return_value = {
            'label': 'some label',
            'entry_date': now,
            'start_date': yesterday,
            'end_date': tomorrow,
            'information_class': 2,
            'altrecordids': {'POLICYID': [self.policy.policy_id]},
        }
        self.ip.submission_agreement = self.sa
        self.ip.save()

        parse_submit_description_from_ip(self.ip)

        self.assertEqual(self.ip.label, "some label")
        self.assertEqual(self.ip.entry_date, now)
        self.assertEqual(self.ip.start_date, yesterday)
        self.assertEqual(self.ip.end_date, tomorrow)
        self.assertEqual(self.ip.information_class, self.policy.information_class)

        mock_parse_desc.assert_called_once()
        mock_agents.assert_called_once()

    @mock.patch('ESSArch_Core.ip.utils.add_agents_from_xml')
    @mock.patch('ESSArch_Core.ip.utils.parse_submit_description')
    def test_parse_submit_desc_with_incorrect_policy(self, mock_parse_desc, mock_agents):
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)

        mock_parse_desc.return_value = {
            'label': 'some label',
            'entry_date': now,
            'start_date': yesterday,
            'end_date': tomorrow,
            'information_class': 2,
            'altrecordids': {'POLICYID': ['incorrect']},
        }
        self.ip.submission_agreement = self.sa
        self.ip.save()

        expected_message = "Policy in submit description ({}) and submission agreement ({}) does not match".format(
            'incorrect', self.sa.policy.policy_id,
        )
        with self.assertRaisesMessage(ValueError, expected_message):
            parse_submit_description_from_ip(self.ip)

    @mock.patch('ESSArch_Core.ip.utils.add_agents_from_xml')
    @mock.patch('ESSArch_Core.ip.utils.parse_submit_description')
    def test_parse_submit_desc_with_policy_without_info_class(self, mock_parse_desc, mock_agents):
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)

        mock_parse_desc.return_value = {
            'label': 'some label',
            'entry_date': now,
            'start_date': yesterday,
            'end_date': tomorrow,
            'altrecordids': {'POLICYID': [self.policy.policy_id]},
        }
        self.ip.submission_agreement = self.sa
        self.ip.save()

        parse_submit_description_from_ip(self.ip)

        self.assertEqual(self.ip.label, "some label")
        self.assertEqual(self.ip.entry_date, now)
        self.assertEqual(self.ip.start_date, yesterday)
        self.assertEqual(self.ip.end_date, tomorrow)
        self.assertEqual(self.ip.information_class, self.policy.information_class)

        mock_parse_desc.assert_called_once()
        mock_agents.assert_called_once()

    @mock.patch('ESSArch_Core.ip.utils.add_agents_from_xml')
    @mock.patch('ESSArch_Core.ip.utils.parse_submit_description')
    def test_parse_submit_desc_no_policy_same_correct_info_class(self, mock_parse_desc, mock_agents):
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)

        mock_parse_desc.return_value = {
            'label': 'some label',
            'entry_date': now,
            'start_date': yesterday,
            'end_date': tomorrow,
            'altrecordids': {'POLICYID': [self.policy.policy_id]},
            'information_class': 2,
        }
        self.ip.submission_agreement = self.sa
        self.ip.save()

        parse_submit_description_from_ip(self.ip)

        self.assertEqual(self.ip.label, "some label")
        self.assertEqual(self.ip.entry_date, now)
        self.assertEqual(self.ip.start_date, yesterday)
        self.assertEqual(self.ip.end_date, tomorrow)
        self.assertEqual(self.ip.information_class, self.policy.information_class)

        mock_parse_desc.assert_called_once()
        mock_agents.assert_called_once()

    @mock.patch('ESSArch_Core.ip.utils.add_agents_from_xml')
    @mock.patch('ESSArch_Core.ip.utils.parse_submit_description')
    def test_parse_submit_desc_no_policy_bad_info_class_should_raise_ValueError(self, mock_parse_desc, mock_agents):
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        yesterday = now - datetime.timedelta(days=1)

        mock_parse_desc.return_value = {
            'label': 'some label',
            'entry_date': now,
            'start_date': yesterday,
            'end_date': tomorrow,
            'altrecordids': {'POLICYID': [self.policy.policy_id]},
            'information_class': 1,
        }

        self.ip.submission_agreement = self.sa
        self.ip.save()

        with self.assertRaisesRegexp(ValueError, "Information class.*{}.*{}.*".format(1, 2)):
            parse_submit_description_from_ip(self.ip)

        self.assertEqual(self.ip.information_class, 1)
        self.assertEqual(self.policy.information_class, 2)

        mock_parse_desc.assert_called_once()
        mock_agents.assert_not_called()


class DownloadSchemaTests(TestCase):

    def setUp(self):
        self.datadir = normalize_path(tempfile.mkdtemp())
        self.textdir = os.path.join(self.datadir, "textdir")
        self.addCleanup(shutil.rmtree, self.datadir)

        os.makedirs(self.textdir)

    @mock.patch('ESSArch_Core.ip.utils.open')
    @mock.patch('ESSArch_Core.ip.utils.requests.get')
    def test_download_schema_should_save_to_file(self, get_requests, mock_open):
        logger = mock.Mock()
        schema = "https://dummy.url.to.xsd"
        get_requests.return_value.raise_for_status.return_value = mock.ANY
        download_schema(dirname=self.textdir, logger=logger, schema=schema, verify=True)

        get_requests.assert_called_once_with(schema, stream=True, verify=True)
        mock_open.assert_called_once_with(os.path.join(self.textdir, "dummy.url.to.xsd"), 'wb')
        self.assertEqual(logger.info.call_count, 2)

    @mock.patch('ESSArch_Core.ip.utils.os.remove')
    @mock.patch('ESSArch_Core.ip.utils.requests.get')
    def test_when_exception_raised_should_log_and_raise(self, get_requests, os_remove):
        logger = mock.Mock()
        schema = "https://dummy.url.to.xsd"
        get_requests.side_effect = Exception

        with self.assertRaises(Exception):
            download_schema(dirname=self.textdir, logger=logger, schema=schema, verify=True)

        get_requests.assert_called_once_with(schema, stream=True, verify=True)
        self.assertEqual(logger.info.call_count, 2)
        self.assertEqual(logger.exception.call_count, 1)
        self.assertEqual(logger.debug.call_count, 1)

    @mock.patch('ESSArch_Core.ip.utils.os.remove')
    @mock.patch('ESSArch_Core.ip.utils.requests.get')
    def test_when_exception_raised_and_failed_to_delete_file_should_log_and_raise(self, get_requests, os_remove):
        logger = mock.Mock()
        schema = "https://dummy.url.to.xsd"
        get_requests.side_effect = Exception
        os_remove.side_effect = OSError

        with self.assertRaises(Exception):
            download_schema(dirname=self.textdir, logger=logger, schema=schema, verify=True)

        get_requests.assert_called_once_with(schema, stream=True, verify=True)
        self.assertEqual(logger.info.call_count, 1)
        self.assertEqual(logger.exception.call_count, 2)
        self.assertEqual(logger.debug.call_count, 1)
