import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from elasticsearch.exceptions import NotFoundError

from ESSArch_Core.auth.models import GroupGenericObjects
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

    try:
        instance.get_doc().delete()
    except NotFoundError:
        logger.warning('TagVersion document not found: {}'.format(instance.pk))


@receiver(post_delete, sender=TagVersion)
def post_tag_version_delete(sender, instance, **kwargs):
    tag = instance.tag

    if not tag.versions.exists():
        tag.delete()


@receiver(post_delete, sender=TagVersion)
def log_after_deleting_tag_version(sender, instance, **kwargs):
    logger.debug(f"TagVersion '{instance}' was deleted.")

    tag_version_content_type = ContentType.objects.get_for_model(instance)
    GroupGenericObjects.objects.filter(object_id=str(instance.pk), content_type=tag_version_content_type).delete()


@receiver(post_delete, sender=Tag)
def log_after_deleting_tag(sender, instance, **kwargs):
    logger.debug(f"Tag '{instance}' was deleted.")
