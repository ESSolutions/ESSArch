import logging

import channels.layers
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.contrib.sessions.models import Session
from django.db import Error
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver
from groups_manager.models import (
    group_member_delete as groups_manager_group_member_delete,
    group_member_save as groups_manager_group_member_save,
)
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_delay,
    wait_random_exponential,
)

from ESSArch_Core.auth.models import (
    Group,
    GroupMember,
    Member,
    Notification,
    ProxyUser,
    UserProfile,
)
from ESSArch_Core.auth.saml.mapping import (
    get_backend as get_saml_mapping_backend,
)
from ESSArch_Core.auth.util import get_organization_groups

User = get_user_model()

if getattr(settings, 'ENABLE_SSO_LOGIN', False) or getattr(settings, 'ENABLE_ADFS_LOGIN', False):
    from djangosaml2.signals import pre_user_save as saml_pre_user_save

    @receiver(saml_pre_user_save, sender=User)
    @receiver(saml_pre_user_save, sender=ProxyUser)
    def saml2_mapping(sender, instance, attributes, user_modified, **kwargs):
        backend = get_saml_mapping_backend()
        if backend is None:
            return user_modified

        backend.map(instance, attributes)
        return user_modified


async def closing_group_send(channel_layer, channel, message):
    await channel_layer.group_send(channel, message)
    await channel_layer.close_pools()


@receiver(post_save, sender=User)
@receiver(post_save, sender=ProxyUser)
def user_post_save(sender, instance, created, *args, **kwargs):
    logger = logging.getLogger('essarch.auth')
    if created or not hasattr(instance, 'user_profile'):
        UserProfile.objects.create(user=instance)

    Member.objects.update_or_create(django_user=instance,
                                    defaults={'username': instance.username, 'first_name': instance.first_name,
                                              'last_name': instance.last_name, 'email': instance.email})

    if created:
        logger.info(f"User '{instance}' was created.")
    else:
        logger.info(f"User '{instance}' was updated.")


@receiver(user_logged_in)
def user_logged_in(sender, user, request, **kwargs):
    logger = logging.getLogger('essarch.auth')
    if user.user_profile.language == '':
        user.user_profile.language = 'DEFAULT'
        user.user_profile.save(update_fields=['language'])

    host = request.META.get('REMOTE_ADDR')
    if host is None:
        logger.info("User {} successfully logged in from unknown host".format(user))
    else:
        logger.info("User {} successfully logged in from host: {}".format(user, host))


@receiver(user_logged_out)
def user_logged_out(sender, user, request, **kwargs):
    logger = logging.getLogger('essarch.auth')
    host = request.META.get('REMOTE_ADDR')
    if host is None:
        logger.info("User {} successfully logged out from unknown host".format(user))
    else:
        logger.info("User {} successfully logged out from host: {}".format(user, host))


@receiver(user_login_failed)
def user_login_failed(sender, credentials, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.warning("Authentication failure with credentials: %s" % (repr(credentials)))


@receiver(pre_delete, sender=Session)
def log_before_deleting_session(sender, instance, **kwargs):
    logger = logging.getLogger('essarch.auth')
    uid = instance.get_decoded().get('_auth_user_id')
    if uid:
        user = User.objects.get(id=uid)
        logger.info(f"Deleting session for user '{user}'.")


@receiver(post_save, sender=Session)
def log_before_creating_session(sender, instance, **kwargs):
    logger = logging.getLogger('essarch.auth')
    uid = instance.get_decoded().get('_auth_user_id')
    if uid:
        user = User.objects.get(id=uid)
        logger.info(f"Created new session for user '{user}'.")


@receiver(pre_save, sender=Group)
def group_pre_save(sender, instance, *args, **kwargs):
    if not hasattr(instance, 'django_group'):
        instance.django_group = DjangoGroup.objects.create(name=instance.name)


@receiver(post_save, sender=Group)
def group_post_save(sender, instance, created, *args, **kwargs):
    logger = logging.getLogger('essarch.auth')
    if created:
        logger.info(f"Created group '{instance.name}'")
    else:
        logger.info(f"Group '{instance.name}' was updated.")


@receiver(post_delete, sender=Group)
def group_post_delete(sender, instance, *args, **kwargs):
    try:
        if hasattr(instance, 'django_group'):
            instance.django_group.delete()
    except DjangoGroup.DoesNotExist:
        pass


@receiver(m2m_changed, sender=ProxyUser.groups.through)
@receiver(m2m_changed, sender=User.groups.through)
def group_users_change(sender, instance, action, reverse, pk_set=None, *args, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.info(f"Changing group for user '{instance}', action: {action}.")
    member = instance.essauth_member
    if action == 'post_add':
        # we use loop instead of bulk_create for easier handling of duplicates in database
        for group_id in pk_set:
            group = Group.objects.get(django_group_id=group_id)
            GroupMember.objects.update_or_create(member=member, group=group)
    elif action == 'post_remove':
        GroupMember.objects.filter(member=member, group__django_group__pk__in=pk_set).delete()
    elif action == 'post_clear':
        GroupMember.objects.filter(member=member).delete()


@receiver(post_save, sender=GroupMember)
def group_member_save(sender, instance, created, *args, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.info(f"User '{instance.member}' is now member of group '{instance.group}'.")
    groups_manager_group_member_save(sender, instance, created, *args, **kwargs)


@receiver(post_delete, sender=GroupMember)
def group_member_delete(sender, instance, *args, **kwargs):
    logger = logging.getLogger('essarch.auth')
    logger.info(f"User '{instance.member}' is no longer member of group '{instance.group}'.")
    groups_manager_group_member_delete(sender, instance, *args, **kwargs)


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    channel_layer = channels.layers.get_channel_layer()
    grp = 'notifications_{}'.format(instance.user.pk)
    for attempt in Retrying(retry=retry_if_exception_type(Error),
                            reraise=True,
                            stop=stop_after_delay(300),
                            wait=wait_random_exponential(multiplier=1, max=10),
                            before_sleep=before_sleep_log(logging.getLogger('essarch'), logging.WARNING)):
        with attempt:
            unseen_count = Notification.objects.filter(user=instance.user, seen=False).count()
    async_to_sync(closing_group_send)(
        channel_layer,
        grp,
        {
            'type': 'notify',
            'id': instance.id,
            'message': instance.message,
            'level': instance.get_level_display(),
            'unseen_count': unseen_count,
            'refresh': instance.refresh,
        })


@receiver(m2m_changed, sender=User.groups.through)
def set_current_organization(sender, instance, action, reverse, *args, **kwargs):

    def set_organization(user):
        groups = get_organization_groups(user)
        current_org = user.user_profile.current_organization

        if current_org not in groups:
            user.user_profile.current_organization = groups.first()

        user.user_profile.save(update_fields=['current_organization'])

    if not reverse:
        user = instance
        set_organization(user)
    else:
        group = instance
        for user in group.user_set.all():
            set_organization(user)


try:
    from django_auth_ldap.backend import LDAPBackend, ldap_error  # isort:skip

    @receiver(ldap_error, sender=LDAPBackend)
    def ldap_failed(sender, context, exception, user=None, **kwargs):
        exc = exception.args[0]
        if 'info' in exc:
            message = '%s: %s' % (exc['desc'], exc['info'])
        else:
            message = exc['desc']

        ldap_logger = logging.getLogger('essarch.auth.ldap')
        ldap_logger.critical(message, exc_info=exception)

        if user is None or user.is_anonymous:
            return

        Notification.objects.create(level=logging.CRITICAL, message=message, user=user)
except ImportError:
    pass
