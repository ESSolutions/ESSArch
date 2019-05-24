from django.db.models.signals import post_save
from django.dispatch import receiver

from ESSArch_Core.storage.models import IOQueue


@receiver(post_save, sender=IOQueue)
def ioqueue_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
    if created or instance.status != 100:
        return

    # The IOQueue entry has failed, mark the storage medium as failed
    if instance.storage_medium is not None:
        instance.storage_medium.status = 100
        instance.storage_medium.save(update_fields=['status'])

    if instance.access_queue is not None and instance.access_queue.status != 100:
        # Set the status to 5 so that on the next poll of the access queue
        # we can look for entries with failed IOQueue entries that might have
        # more available storage objects on other mediums

        instance.access_queue.status = 5
        instance.access_queue.save(update_fields=['status'])
