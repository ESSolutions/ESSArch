import os
import shutil
import tempfile

from django.template import TemplateDoesNotExist
from django.test import TestCase

from ESSArch_Core.configuration.models import Path
from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob


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
