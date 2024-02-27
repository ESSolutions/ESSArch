from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.utils import timezone

# noinspection PyUnresolvedReferences
from ESSArch_Core import tasks  # noqa
from ESSArch_Core.config.celery import app
from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob
from ESSArch_Core.WorkflowEngine.models import ProcessTask

User = get_user_model()


@app.task(bind=True)
def RunAppraisalJob(self, pk):
    job = AppraisalJob.objects.get(pk=pk)
    return job.run()


@app.task(bind=True)
def RunConversionJob(self, pk):
    job = ConversionJob.objects.get(pk=pk)
    return job.run()


@app.task(bind=True, track=False)
def PollAppraisalJobs(self):
    now = timezone.now()
    jobs = AppraisalJob.objects.select_related('template').filter(
        status=celery_states.PENDING, start_date__lte=now,
    )

    for job in jobs.iterator(chunk_size=1000):
        if job.task is None:
            job.task = ProcessTask.objects.create(
                name='ESSArch_Core.maintenance.tasks.RunAppraisalJob',
                args=[str(job.pk)],
                eager=False,
            )
            job.save(update_fields=['task'])
        job.run()


@app.task(bind=True, track=False)
def PollConversionJobs(self):
    now = timezone.now()
    jobs = ConversionJob.objects.select_related('template').filter(
        status=celery_states.PENDING, start_date__lte=now,
    )

    for job in jobs.iterator(chunk_size=1000):
        if job.task is None:
            job.task = ProcessTask.objects.create(
                name='ESSArch_Core.maintenance.tasks.RunConversionJob',
                args=[str(job.pk)],
                eager=False,
            )
            job.save(update_fields=['task'])
        job.run()
