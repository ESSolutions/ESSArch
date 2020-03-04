import shutil
import tempfile
from datetime import timedelta

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ESSArch_Core.configuration.models import EventType, Path
from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob
from ESSArch_Core.testing.runner import TaskRunner
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


class PollAppraisalJobs(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)
        Path.objects.create(entity='temp', value=tempfile.mkdtemp(dir=self.datadir))
        Path.objects.create(entity='appraisal_reports', value=tempfile.mkdtemp(dir=self.datadir))
        EventType.objects.create(eventType=50710, category=EventType.CATEGORY_INFORMATION_PACKAGE)

    def create_task(self):
        return ProcessTask.objects.create(
            name='ESSArch_Core.maintenance.tasks.PollAppraisalJobs',
        )

    @TaskRunner()
    def test_no_jobs(self):
        task = self.create_task()
        task.run()

    @TaskRunner()
    def test_no_pending_scheduled_jobs(self):
        job = AppraisalJob.objects.create()

        task = self.create_task()
        task.run()

        job.refresh_from_db()
        self.assertEqual(job.status, celery_states.PENDING)
        self.assertIsNone(job.start_date)

    @TaskRunner()
    def test_pending_scheduled_job(self):
        job = AppraisalJob.objects.create(start_date=timezone.now() + timedelta(days=10))
        task = self.create_task()
        task.run()

        job.refresh_from_db()
        self.assertEqual(job.status, celery_states.PENDING)

        job.start_date = timezone.now()
        job.save()

        task = self.create_task()
        task.run()

        job.refresh_from_db()
        self.assertEqual(job.status, celery_states.SUCCESS)


class PollConversionJobs(TestCase):
    def setUp(self):
        self.datadir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.datadir)
        Path.objects.create(entity='temp', value=tempfile.mkdtemp(dir=self.datadir))
        Path.objects.create(entity='conversion_reports', value=tempfile.mkdtemp(dir=self.datadir))

    def create_task(self):
        return ProcessTask.objects.create(
            name='ESSArch_Core.maintenance.tasks.PollConversionJobs',
        )

    @TaskRunner()
    def test_no_jobs(self):
        task = self.create_task()
        task.run()

    @TaskRunner()
    def test_no_pending_scheduled_jobs(self):
        job = ConversionJob.objects.create()

        task = self.create_task()
        task.run()

        job.refresh_from_db()
        self.assertEqual(job.status, celery_states.PENDING)
        self.assertIsNone(job.start_date)

    @TaskRunner()
    def test_pending_scheduled_job(self):
        job = ConversionJob.objects.create(start_date=timezone.now() + timedelta(days=10))
        task = self.create_task()
        task.run()

        job.refresh_from_db()
        self.assertEqual(job.status, celery_states.PENDING)

        job.start_date = timezone.now()
        job.save()

        task = self.create_task()
        task.run()

        job.refresh_from_db()
        self.assertEqual(job.status, celery_states.SUCCESS)
