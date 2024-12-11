import logging

from celery.signals import task_received, task_revoked
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


@receiver(pre_save, sender=ProcessTask)
def task_pre_save(sender, instance, **kwargs):
    if not instance.label:
        instance.label = instance.name


@receiver(post_save, sender=ProcessTask)
def task_post_save(sender, instance, created, **kwargs):
    try:
        instance.processstep.clear_cache()
    except AttributeError:
        pass


@receiver(post_save, sender=ProcessStep)
def step_post_save(sender, instance, created, **kwargs):
    try:
        instance.parent.clear_cache()
    except AttributeError:
        pass


@task_received.connect
def task_received_handler(request=None, **kwargs):
    logger = logging.getLogger('essarch')
    try:
        t = ProcessTask.objects.get(celery_id=request.task_id)
        logger.debug('{} signal task_received status is {}'.format(request.task_id, repr(t.status)))
        if t.status == 'REVOKED':
            t.revoke()
    except ProcessTask.DoesNotExist:
        logger.debug('{} signal task_received without ProcessTask'.format(request.task_id))
        pass


@task_revoked.connect
def task_revoked_handler(request=None, **kwargs):
    logger = logging.getLogger('essarch')
    logger.debug('{} signal task_revoked'.format(request.id))
