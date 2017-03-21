from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from ESSArch_Core.auth.models import UserProfile


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created or not hasattr(instance, 'user_profile'):
        UserProfile.objects.create(user=instance)
