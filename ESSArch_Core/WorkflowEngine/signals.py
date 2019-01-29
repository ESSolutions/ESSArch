from django.db.models.signals import pre_save, post_save
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
        instance.parent_step.clear_cache()
    except AttributeError:
        pass
