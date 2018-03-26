import json
import logging

from channels import Channel
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DjangoGroup
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, pre_save, post_save
from django.dispatch import receiver
from groups_manager.models import group_member_delete as groups_manager_group_member_delete
from groups_manager.models import group_member_save as groups_manager_group_member_save

from ESSArch_Core.auth.models import Group, GroupMember, Member, Notification, ProxyUser, UserProfile
from ESSArch_Core.auth.util import get_organization_groups

User = get_user_model()


@receiver(post_save, sender=User)
@receiver(post_save, sender=ProxyUser)
def user_post_save(sender, instance, created, *args, **kwargs):
    if created or not hasattr(instance, 'user_profile'):
        UserProfile.objects.create(user=instance)

    Member.objects.update_or_create(django_user=instance,
                                    defaults={'username': instance.username, 'first_name': instance.first_name,
                                              'last_name': instance.last_name, 'email': instance.email})


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


@receiver(pre_save, sender=Group)
def group_pre_save(sender, instance, *args, **kwargs):
    if not hasattr(instance, 'django_group'):
        instance.django_group = DjangoGroup.objects.create(name=instance.name)


@receiver(m2m_changed, sender=ProxyUser.groups.through)
@receiver(m2m_changed, sender=User.groups.through)
def group_users_change(sender, instance, action, reverse, pk_set=None, *args, **kwargs):
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
    groups_manager_group_member_save(sender, instance, created, *args, **kwargs)


@receiver(post_delete, sender=GroupMember)
def group_member_delete(sender, instance, *args, **kwargs):
    groups_manager_group_member_delete(sender, instance, *args, **kwargs)


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
                        'refresh': instance.refresh,
                    })
                }, immediately=True)
            except c.channel_layer.ChannelFull:
                channels.discard(channel)
                cache.set(cache_name, channels)


@receiver(m2m_changed, sender=User.groups.through)
def set_default_organization(sender, instance, action, reverse, *args, **kwargs):

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
        message = '%s: %s' % (exception.message['desc'], exception.message['info'])

        logger = logging.getLogger('essarch.auth.ldap')
        logger.critical(message)

        if user is None:
            return

        Notification.objects.create(level=logging.CRITICAL, message=message, user=user)
except ImportError:
    pass
