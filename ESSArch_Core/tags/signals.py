import logging

import six
from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver
from django_redis import get_redis_connection
from elasticsearch_dsl.connections import get_connection
from six.moves import cPickle

from ESSArch_Core.tags import DELETION_QUEUE, INDEX_QUEUE, UPDATE_QUEUE
from ESSArch_Core.tags.models import TagStructure, TagVersion

logger = logging.getLogger('essarch.core')


@receiver(post_save, sender=TagVersion)
def set_current_version_after_creation(sender, instance, created, **kwargs):
    if created and instance.tag.current_version is None:
        tag = instance.tag
        tag.current_version = instance
        tag.save(update_fields=['current_version'])


@receiver(pre_delete, sender=TagVersion)
def fix_current_version_before_version_delete(sender, instance, **kwargs):
    if instance.tag.current_version == instance:
        try:
            tag = instance.tag
            tag.current_version = tag.versions.exclude(pk=instance.pk).latest()
            tag.save(update_fields=['current_version'])
        except TagVersion.DoesNotExist:
            pass
