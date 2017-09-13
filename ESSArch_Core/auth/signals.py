import logging

from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from ESSArch_Core.auth.models import UserProfile


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created or not hasattr(instance, 'user_profile'):
        UserProfile.objects.create(user=instance)


@receiver(user_logged_in)
def user_logged_in(sender, user, request, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.info("User %s successfully logged in from host: %s" % (user, request.META['REMOTE_ADDR']))


@receiver(user_logged_out)
def user_logged_out(sender, user, request, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.info("User %s successfully logged out from host: %s" % (user, request.META['REMOTE_ADDR']))


@receiver(user_login_failed)
def user_login_failed(sender, credentials, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.warning("Authentication failure with credentials: %s" % (repr(credentials)))
