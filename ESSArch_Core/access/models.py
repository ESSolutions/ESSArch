import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from languages_plus.models import Language

from ESSArch_Core.auth.models import GroupGenericObjects
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

    def get_organization(self):
        ctype = ContentType.objects.get_for_model(self)
        gg_obj = GroupGenericObjects.objects.get(object_id=self.pk, content_type=ctype)

        return gg_obj

    def __str__(self):
        return self.name



class AccessAidType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('access aid type')
        verbose_name_plural = _('access aid types')
