from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.utils import timezone

# noinspection PyUnresolvedReferences
from ESSArch_Core import tasks  # noqa
from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob
from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


class RunAppraisalJob(DBTask):
    def run(self, pk):
        job = AppraisalJob.objects.get(pk=pk)
        return job.run()


class RunConversionJob(DBTask):
    def run(self, pk):
        job = ConversionJob.objects.get(pk=pk)
        return job.run()


class PollAppraisalJobs(DBTask):
    track = False

    def run(self):
        now = timezone.now()
        jobs = AppraisalJob.objects.select_related('template').filter(
            status=celery_states.PENDING, start_date__lte=now,
        )

        for job in jobs.iterator():
            if job.task is None:
                job.task = ProcessTask.objects.create(
                    name='ESSArch_Core.maintenance.tasks.RunAppraisalJob',
                    args=[str(job.pk)],
                    eager=False,
                )
                job.save(update_fields=['task'])
            job.run()


class PollConversionJobs(DBTask):
    track = False

    def run(self):
        now = timezone.now()
        jobs = ConversionJob.objects.select_related('template').filter(
            status=celery_states.PENDING, start_date__lte=now,
        )

        for job in jobs.iterator():
            if job.task is None:
                job.task = ProcessTask.objects.create(
                    name='ESSArch_Core.maintenance.tasks.RunConversionJob',
                    args=[str(job.pk)],
                    eager=False,
                )
                job.save(update_fields=['task'])
            job.run()
