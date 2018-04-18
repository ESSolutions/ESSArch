import errno
import logging
import os
import shutil

from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver

from ESSArch_Core.ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    InformationPackage, Workarea,
)


logger = logging.getLogger('essarch.core')

@receiver(pre_delete, sender=InformationPackage)
def ip_pre_delete(sender, instance, using, **kwargs):
    logger.debug('Deleting information package %s' % instance.pk)


@receiver(post_delete, sender=InformationPackage)
def ip_post_delete(sender, instance, using, **kwargs):
    logger.info('Information package %s was deleted' % instance.pk)

    if instance.aic is not None and not instance.aic.information_packages.exists():
        # this was the last IP in the AIC, delete the AIC as well
        instance.aic.delete()


@receiver(post_delete, sender=Workarea)
def workarea_post_delete(sender, instance, using, **kwargs):
    try:
        shutil.rmtree(instance.path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    try:
        os.remove(instance.path + '.tar')
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
