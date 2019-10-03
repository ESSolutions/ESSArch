import logging

from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from ESSArch_Core.tags.models import Tag, TagVersion

logger = logging.getLogger('essarch.core')


@receiver(post_save, sender=TagVersion)
def set_current_version_after_creation(sender, instance, created, **kwargs):
    if created and instance.tag.current_version is None:
        logger.debug(f"TagVersion '{instance}' was created.")
        tag = instance.tag
        tag.current_version = instance
        tag.save(update_fields=['current_version'])
    else:
        logger.debug(f"TagVersion '{instance}' was updated.")


@receiver(pre_delete, sender=TagVersion)
def pre_tag_version_delete(sender, instance, **kwargs):
    logger.debug(f"Changing current version of TagVersion: '{instance}', before deleting.")
    if instance.tag.current_version == instance:
        try:
            tag = instance.tag
            tag.current_version = tag.versions.exclude(pk=instance.pk).latest()
            tag.save(update_fields=['current_version'])
        except TagVersion.DoesNotExist:
            pass

    instance.get_doc().delete()


@receiver(post_delete, sender=TagVersion)
def log_after_deleting_tag_version(sender, instance, **kwargs):
    logger.debug(f"TagVersion '{instance}' was deleted.")


@receiver(post_delete, sender=Tag)
def log_after_deleting_tag(sender, instance, **kwargs):
    logger.debug(f"Tag '{instance}' was deleted.")
