import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from redis import StrictRedis
from six.moves import cPickle

from ESSArch_Core.tags import DELETION_QUEUE, INDEX_QUEUE, UPDATE_QUEUE
from ESSArch_Core.tags.models import TagVersion

logger = logging.getLogger('essarch.core')
r = StrictRedis()


@receiver(post_save, sender=TagVersion)
def queue_tag_for_index(sender, instance, created, **kwargs):
    if created:
        if instance.tag.current_version is None:
            tag = instance.tag
            tag.current_version = instance
            tag.save(update_fields=['current_version'])

    data = {
        '_op_type': 'update',
        'doc_as_upsert': True,
        '_index': instance.elastic_index,
        '_type': 'doc',
        '_id': str(instance.pk),
        'doc': {
            'name': instance.name,
            'type': instance.type,
        },
    }
    r.rpush(UPDATE_QUEUE, cPickle.dumps(data))


@receiver(post_delete, sender=TagVersion)
def queue_tag_for_deletion(sender, instance, **kwargs):
    if instance.tag.current_version is None:
        try:
            tag = instance.tag
            tag.current_version = tag.versions.latest()
            tag.save(update_fields=['current_version'])
        except TagVersion.DoesNotExist:
            pass

    data = {
        '_op_type': 'delete',
        '_index': instance.elastic_index,
        '_type': 'doc',
        '_id': str(instance.pk),
    }
    r.rpush(DELETION_QUEUE, cPickle.dumps(data))
