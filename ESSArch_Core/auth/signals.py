import json
import logging

from channels import Channel
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from ESSArch_Core.auth.models import Notification, UserProfile


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


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    cache_name = 'notification_channel_%s' % instance.user.username
    channels = cache.get(cache_name)

    if channels is not None:
        for channel in channels.copy():
            c = Channel(channel)
            try:
                c.send({
                    "text": json.dumps({
                        'id': instance.id,
                        'message': instance.message,
                        'level': instance.get_level_display(),
                        'unseen_count': Notification.objects.filter(user=instance.user, seen=False).count(),
                    })
                }, immediately=True)
            except c.channel_layer.ChannelFull:
                channels.discard(channel)
                cache.set(cache_name, channels)


try:
    from django_auth_ldap.backend import LDAPBackend, ldap_error  # isort:skip

    @receiver(ldap_error, sender=LDAPBackend)
    def ldap_failed(sender, context, exception, user=None, **kwargs):
        message = '%s: %s' % (exception.message['desc'], exception.message['info'])

        logger = logging.getLogger('essarch.auth.ldap')
        logger.critical(message)

        if user is None:
            return

        Notification.objects.create(level=logging.CRITICAL, message=message, user=user)
except ImportError:
    pass
