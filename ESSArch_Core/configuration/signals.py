from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from ESSArch_Core.configuration.models import EventType, Parameter


@receiver(post_save, sender=EventType)
def event_type_post_save(sender, instance, created, **kwargs):
    cache_name = 'event_type_%s_enabled' % instance.eventType
    cache.set(cache_name, instance.enabled, 3600)

@receiver(post_save, sender=Parameter)
def parameter_post_save(sender, instance, created, **kwargs):
    cache_name = 'parameter_%s' % instance.entity
    cache.set(cache_name, instance.value, 3600)
