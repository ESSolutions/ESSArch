import logging

from django.db.models.signals import pre_delete, post_delete, post_save
from django.dispatch import receiver
from elasticsearch import Elasticsearch
from redis import StrictRedis
from six.moves import cPickle

from ESSArch_Core.tags import DELETION_QUEUE, INDEX_QUEUE, UPDATE_QUEUE
from ESSArch_Core.tags.models import TagVersion

logger = logging.getLogger('essarch.core')
es = Elasticsearch()
r = StrictRedis()


@receiver(post_save, sender=TagVersion)
def queue_tag_for_index(sender, instance, created, **kwargs):
    if created:
        if instance.tag.current_version is None:
            tag = instance.tag
            tag.current_version = instance
            tag.save(update_fields=['current_version'])

    data = {
        'doc_as_upsert': True,
        'doc': {
            'reference_code': instance.reference_code,
            'name': instance.name,
            'type': instance.type,
            'current_version': instance.tag.current_version == instance
        },
    }

    if instance.elastic_index != 'archive':
        archive = instance.get_root()
        if archive is not None:
            data['doc']['archive'] = str(archive.pk)
    es.update(instance.elastic_index, 'doc', str(instance.pk), body=data)


@receiver(pre_delete, sender=TagVersion)
def fix_current_version_before_version_delete(sender, instance, **kwargs):
    if instance.tag.current_version == instance:
        try:
            tag = instance.tag
            tag.current_version = tag.versions.exclude(pk=instance.pk).latest()
            tag.save(update_fields=['current_version'])
        except TagVersion.DoesNotExist:
            pass


@receiver(post_delete, sender=TagVersion)
def queue_tag_for_deletion(sender, instance, **kwargs):
    data = {
        '_op_type': 'delete',
        '_index': instance.elastic_index,
        '_type': 'doc',
        '_id': str(instance.pk),
    }
    r.rpush(DELETION_QUEUE, cPickle.dumps(data))
