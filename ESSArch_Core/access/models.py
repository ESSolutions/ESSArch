import uuid

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from ESSArch_Core.auth.models import GroupObjectsBase
from ESSArch_Core.auth.util import get_group_objs_model
from ESSArch_Core.managers import OrganizationManager


class AccessAid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    type = models.ForeignKey('access.AccessAidType', on_delete=models.PROTECT, null=False, related_name='access_aids')
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    security_level = models.IntegerField(_('security level'), null=True)
    link = models.TextField(_('link'), blank=True)

    objects = OrganizationManager()

    @transaction.atomic
    def change_organization(self, organization):
        group_objs_model = get_group_objs_model(self)
        group_objs_model.objects.change_organization(self, organization)

    def get_organization(self):
        group_objs_model = get_group_objs_model(self)
        return group_objs_model.objects.get_organization(self)

    def __str__(self):
        return self.name


class AccessAidUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(AccessAid, on_delete=models.CASCADE)


class AccessAidGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(AccessAid, on_delete=models.CASCADE)


class AccessAidGroupObjects(GroupObjectsBase):
    content_object = models.ForeignKey(AccessAid, on_delete=models.CASCADE)


class AccessAidType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('access aid type')
        verbose_name_plural = _('access aid types')
