import uuid

from django.db import models

from mptt.models import MPTTModel, TreeForeignKey

from ESSArch_Core.ip.models import InformationPackage


class Tag(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Name', max_length=255)
    desc = models.CharField('Description', max_length=255, blank=True)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True)
    information_packages = models.ManyToManyField(InformationPackage, related_name='tags')

    class Meta:
        permissions = (
            ('search', 'Can search'),
            ('view_pul', 'Can view PuL'),
        )

    def __unicode__(self):
        return self.name

    class MPTTMeta:
        order_insertion_by = ['name']
