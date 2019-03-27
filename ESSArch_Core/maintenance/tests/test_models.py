import os
import shutil
import tempfile
from unittest import mock
from stat import S_IWRITE

from django.template import TemplateDoesNotExist
from django.test import TestCase
from celery import states as celery_states
from django.utils import timezone

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import (
    AppraisalJob,
    ConversionJob,
    find_all_files,
)
from ESSArch_Core.util import normalize_path, win_to_posix


class MaintenanceJobGetReportDirectoryTests(TestCase):

    def test_get_report_directory_entity_when_path_doesnt_exist_should_raise_exception(self):
        appraisal_job = AppraisalJob.objects.create()
        conversion_job = ConversionJob.objects.create()

        with self.assertRaisesRegex(Path.DoesNotExist, 'Path appraisal_reports is not configured'):
            appraisal_job._get_report_directory()

        with self.assertRaisesRegex(Path.DoesNotExist, 'Path conversion_reports is not configured'):
            conversion_job._get_report_directory()

    def test_get_report_directory_entity_when_path_exist(self):
        appraisal_job = AppraisalJob.objects.create()
        conversion_job = ConversionJob.objects.create()
        Path.objects.create(entity="appraisal_reports", value="expected_path_value_for_appraisal")
        Path.objects.create(entity="conversion_reports", value="expected_path_value_for_conversion")

        self.assertEqual(appraisal_job._get_report_directory(), "expected_path_value_for_appraisal")
        self.assertEqual(conversion_job._get_report_directory(), "expected_path_value_for_conversion")


class MaintenanceJobGenerateReportTests(TestCase):

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.appraisal_path = os.path.join(self.datadir, 'appraisal_path')
        self.conversion_path = os.path.join(self.datadir, 'conversion_path')
        self.addCleanup(shutil.rmtree, self.datadir)

        try:
            os.makedirs(self.appraisal_path)
            os.makedirs(self.conversion_path)
        except OSError as e:
            if e.errno != 17:
                raise

    def test_generate_report_when_all_fine(self):
        appraisal_job = AppraisalJob.objects.create()
        conversion_job = ConversionJob.objects.create()
        Path.objects.create(entity="appraisal_reports", value=self.appraisal_path)
        Path.objects.create(entity="conversion_reports", value=self.conversion_path)

        appraisal_pdf_path = os.path.join(self.appraisal_path, f"{appraisal_job.pk}.pdf")
        conversion_pdf_path = os.path.join(self.conversion_path, f"{conversion_job.pk}.pdf")
        # Make sure files does not exist
        self.assertFalse(os.path.isfile(appraisal_pdf_path))
        self.assertFalse(os.path.isfile(conversion_pdf_path))

        appraisal_job._generate_report()
        conversion_job._generate_report()

        self.assertTrue(os.path.isfile(appraisal_pdf_path))
        self.assertTrue(os.path.isfile(conversion_pdf_path))

    def test_generate_report_when_template_file_missing(self):
        appraisal_job = AppraisalJob.objects.create()
        Path.objects.create(entity="dummy_type_reports", value=self.appraisal_path)
        appraisal_job.MAINTENANCE_TYPE = "dummy_type"

        with self.assertRaisesRegex(TemplateDoesNotExist, "maintenance/dummy_type_report.html"):
            appraisal_job._generate_report()


class MaintenanceJobMarkAsCompleteTests(TestCase):

    def setUp(self):
        self.now = timezone.now()

    @mock.patch('ESSArch_Core.maintenance.models.timezone.now')
    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._generate_report')
    def test_mark_as_complete_when_all_fine(self, mock_generate_report, mock_timezone_now):
        mock_timezone_now.return_value = self.now
        appraisal_job = AppraisalJob.objects.create()
        conversion_job = ConversionJob.objects.create()

        self.assertEqual(appraisal_job.status, celery_states.PENDING)
        self.assertEqual(appraisal_job.end_date, None)
        self.assertEqual(conversion_job.status, celery_states.PENDING)
        self.assertEqual(conversion_job.end_date, None)

        appraisal_job._mark_as_complete()
        conversion_job._mark_as_complete()

        appraisal_job.refresh_from_db()
        conversion_job.refresh_from_db()

        self.assertEqual(mock_generate_report.call_count, 2)
        self.assertEqual(appraisal_job.status, celery_states.SUCCESS)
        self.assertEqual(appraisal_job.end_date, self.now)
        self.assertEqual(conversion_job.status, celery_states.SUCCESS)
        self.assertEqual(conversion_job.end_date, self.now)

    @mock.patch('ESSArch_Core.maintenance.models.timezone.now')
    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._generate_report')
    def test_mark_as_complete_when_report_generation_raised_exception(self, mock_generate_report, mock_timezone_now):
        mock_generate_report.side_effect = Exception()
        mock_timezone_now.return_value = self.now
        appraisal_job = AppraisalJob.objects.create()
        conversion_job = ConversionJob.objects.create()

        self.assertEqual(appraisal_job.status, celery_states.PENDING)
        self.assertEqual(appraisal_job.end_date, None)
        self.assertEqual(conversion_job.status, celery_states.PENDING)
        self.assertEqual(conversion_job.end_date, None)

        with self.assertRaises(Exception):
            appraisal_job._mark_as_complete()

        with self.assertRaises(Exception):
            conversion_job._mark_as_complete()

        appraisal_job.refresh_from_db()
        conversion_job.refresh_from_db()

        self.assertEqual(mock_generate_report.call_count, 2)
        self.assertEqual(appraisal_job.status, celery_states.SUCCESS)
        self.assertEqual(appraisal_job.end_date, self.now)
        self.assertEqual(conversion_job.status, celery_states.SUCCESS)
        self.assertEqual(conversion_job.end_date, self.now)


class MaintenanceJobRunTests(TestCase):

    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)

        self.appraisal_job = AppraisalJob.objects.create()
        self.conversion_job = ConversionJob.objects.create()

        self.appraisal_path = os.path.join(self.datadir, 'appraisal_path')
        self.conversion_path = os.path.join(self.datadir, 'conversion_path')

    def create_paths(self, create_dir, has_access=True):

        if create_dir:
            try:
                os.makedirs(self.appraisal_path)
                os.makedirs(self.conversion_path)

                if not has_access:
                    os.chmod(self.appraisal_path, S_IWRITE & 0)
                    os.chmod(self.conversion_path, S_IWRITE & 0)
            except OSError as e:
                if e.errno != 17:
                    raise
        else:
            assert not os.path.isdir(self.appraisal_path)
            assert not os.path.isdir(self.conversion_path)

    def reset_access_rights(self):
        os.chmod(self.appraisal_path, 0o7777)
        os.chmod(self.conversion_path, 0o7777)

    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._mark_as_complete')
    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._get_report_directory')
    @mock.patch('ESSArch_Core.maintenance.models.ConversionJob._run')
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob._run')
    def test_call_run_when_report_dir_does_not_exists(self, apr_run, con_run, get_report_directory, mark_as_complete):
        before = timezone.now()
        self.create_paths(create_dir=False)
        get_report_directory.side_effect = [self.appraisal_path, self.conversion_path]

        with self.assertRaisesRegex(OSError, f".* No such file or directory: '{self.appraisal_path}'"):
            self.appraisal_job.run()

        with self.assertRaisesRegex(OSError, f".* No such file or directory: '{self.conversion_path}'"):
            self.conversion_job.run()

        after = timezone.now()

        apr_run.assert_not_called()
        con_run.assert_not_called()
        mark_as_complete.assert_not_called()

        # Update object form DB
        self.appraisal_job.refresh_from_db()
        self.conversion_job.refresh_from_db()

        self.assertEqual(self.appraisal_job.status, celery_states.FAILURE)
        self.assertTrue(before <= self.appraisal_job.end_date <= after)
        self.assertEqual(self.conversion_job.status, celery_states.FAILURE)
        self.assertTrue(before <= self.conversion_job.end_date <= after)

    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._mark_as_complete')
    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._get_report_directory')
    @mock.patch('ESSArch_Core.maintenance.models.ConversionJob._run')
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob._run')
    def test_call_run_when_report_dir_is_not_writeable(self, apr_run, con_run, get_report_directory, mark_as_complete):
        before = timezone.now()
        self.create_paths(create_dir=True, has_access=False)
        get_report_directory.side_effect = [self.appraisal_path, self.conversion_path]

        with self.assertRaisesRegex(OSError, f".* Permission denied: '{self.appraisal_path}'"):
            self.appraisal_job.run()

        with self.assertRaisesRegex(OSError, f".* Permission denied: '{self.conversion_path}'"):
            self.conversion_job.run()

        self.reset_access_rights()

        after = timezone.now()

        apr_run.assert_not_called()
        con_run.assert_not_called()
        mark_as_complete.assert_not_called()

        # Update object form DB
        self.appraisal_job.refresh_from_db()
        self.conversion_job.refresh_from_db()

        self.assertEqual(self.appraisal_job.status, celery_states.FAILURE)
        self.assertTrue(before <= self.appraisal_job.end_date <= after)
        self.assertEqual(self.conversion_job.status, celery_states.FAILURE)
        self.assertTrue(before <= self.conversion_job.end_date <= after)

    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._mark_as_complete')
    @mock.patch('ESSArch_Core.maintenance.models.MaintenanceJob._get_report_directory')
    @mock.patch('ESSArch_Core.maintenance.models.ConversionJob._run')
    @mock.patch('ESSArch_Core.maintenance.models.AppraisalJob._run')
    def test_call_success(self, mock_appr__run, mock_con__run, mock__get_report_directory, mock__mark_as_complete):
        self.create_paths(create_dir=True, has_access=True)
        mock__get_report_directory.side_effect = [self.appraisal_path, self.conversion_path]

        self.appraisal_job.run()
        self.conversion_job.run()

        mock_appr__run.assert_called_once()
        mock_con__run.assert_called_once()
        mock__mark_as_complete.assert_called()

        # Update object form DB
        self.appraisal_job.refresh_from_db()
        self.conversion_job.refresh_from_db()

        self.assertEqual(self.appraisal_job.status, celery_states.STARTED)
        self.assertEqual(self.appraisal_job.end_date, None)
        self.assertEqual(self.conversion_job.status, celery_states.STARTED)
        self.assertEqual(self.conversion_job.end_date, None)


class FindAllFilesTests(TestCase):

    def setUp(self):
        self.tmpdir = normalize_path(tempfile.mkdtemp())
        self.datadir = os.path.join(self.tmpdir, "datadir")
        self.addCleanup(shutil.rmtree, self.datadir)
        self.dir_names = [
            'a_dir', 'b_dir', 'c_dir',
            'aa_dir', 'bb_dir', 'cc_dir',
            'ab_dir', 'ac_dir',
            'ba_dir', 'bc_dir',
            'ca_dir', 'cb_dir',
            'a_dir/ca_dir', 'b_dir/cb_dir',
        ]
        self.ip = InformationPackage.objects.create(
            object_path=self.datadir,
            object_identifier_value="ip_obj_id_value"
        )

    def create_dirs_and_files(self):
        for d in self.dir_names:
            try:
                os.makedirs(os.path.join(self.datadir, d))
            except OSError as e:
                if e.errno != 17:
                    raise

        files = []
        for d in self.dir_names:
            for i in range(3):
                fname = os.path.join(self.datadir, os.path.join(d, f"{i}.txt"))
                with open(fname, 'w') as f:
                    f.write(f"{i}")
                files.append(fname)

        return files

    def normalize_paths(self, expected_file_names):
        return [win_to_posix(f) for f in expected_file_names]

    def test_find_all_files_when_pattern_is_star(self):
        files = self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([fi.replace(os.path.join(self.datadir, ""), "") for fi in files])

        found_files = find_all_files(self.datadir, self.ip, "*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')

        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_ends_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/0.txt', 'a_dir/1.txt', 'a_dir/2.txt',
            'aa_dir/0.txt', 'aa_dir/1.txt', 'aa_dir/2.txt',
            'ab_dir/0.txt', 'ab_dir/1.txt', 'ab_dir/2.txt',
            'ac_dir/0.txt', 'ac_dir/1.txt', 'ac_dir/2.txt',
            'a_dir/ca_dir/0.txt', 'a_dir/ca_dir/1.txt', 'a_dir/ca_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "a*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_start_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/2.txt', 'aa_dir/2.txt', 'ab_dir/2.txt', 'ac_dir/2.txt', 'a_dir/ca_dir/2.txt',
            'b_dir/2.txt', 'ba_dir/2.txt', 'bb_dir/2.txt', 'bc_dir/2.txt', 'b_dir/cb_dir/2.txt',
            'c_dir/2.txt', 'ca_dir/2.txt', 'cb_dir/2.txt', 'cc_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "**/2.txt")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)

    def test_find_all_files_when_pattern_is_matching_pattern_which_starts_and_ends_with_star(self):
        self.create_dirs_and_files()
        expected_file_names = self.normalize_paths([
            'a_dir/2.txt', 'aa_dir/2.txt', 'ab_dir/2.txt', 'ac_dir/2.txt', 'a_dir/ca_dir/2.txt',
            'b_dir/2.txt', 'ba_dir/2.txt', 'bb_dir/2.txt', 'bc_dir/2.txt', 'b_dir/cb_dir/2.txt',
            'c_dir/2.txt', 'ca_dir/2.txt', 'cb_dir/2.txt', 'cc_dir/2.txt',
        ])
        found_files = find_all_files(self.datadir, self.ip, "**/2*")
        docs = self.normalize_paths([e['document'] for e in found_files])

        for e in found_files:
            self.assertEqual(e['ip'], 'ip_obj_id_value')
        self.assertCountEqual(expected_file_names, docs)
