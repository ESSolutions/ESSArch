import logging

from django.db.models.signals import pre_delete, post_save, post_delete
from django.dispatch import receiver

from ESSArch_Core.tags.models import TagVersion, Tag

logger = logging.getLogger('essarch.core')


@receiver(post_save, sender=TagVersion)
def set_current_version_after_creation(sender, instance, created, **kwargs):
    if created and instance.tag.current_version is None:
        logger.info(f"TagVersion '{instance}' was created!")
        tag = instance.tag
        tag.current_version = instance
        tag.save(update_fields=['current_version'])
    else:
        logger.info(f"TagVersion '{instance}' was updated!")


@receiver(pre_delete, sender=TagVersion)
def fix_current_version_before_version_delete(sender, instance, **kwargs):
    logger.info(f"Changing current version of TagVersion: '{instance}', before deleting!")
    if instance.tag.current_version == instance:
        try:
            tag = instance.tag
            tag.current_version = tag.versions.exclude(pk=instance.pk).latest()
            tag.save(update_fields=['current_version'])
        except TagVersion.DoesNotExist:
            pass


@receiver(post_delete, sender=TagVersion)
def log_after_deleting_tag_version(sender, instance, **kwargs):
    logger.info(f"TagVersion '{instance}' was deleted!")


@receiver(post_delete, sender=Tag)
def log_after_deleting_tag(sender, instance, **kwargs):
    logger.info(f"Tag '{instance}' was deleted!")
