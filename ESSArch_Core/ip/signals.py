import errno
import logging
import os
import shutil

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from ESSArch_Core.auth.models import GroupGenericObjects
from ESSArch_Core.ip.models import InformationPackage, Workarea

logger = logging.getLogger('essarch.core')


@receiver(pre_delete, sender=InformationPackage)
def ip_pre_delete(sender, instance, using, **kwargs):
    logger.debug('Deleting information package %s' % instance.pk)


@receiver(post_delete, sender=InformationPackage)
def ip_post_delete(sender, instance, using, **kwargs):
    logger.info('Information package %s was deleted' % instance.pk)

    ip_content_type = ContentType.objects.get_for_model(instance)
    GroupGenericObjects.objects.filter(object_id=str(instance.pk), content_type=ip_content_type).delete()

    try:
        if instance.aic is not None and not instance.aic.information_packages.exists():
            # this was the last IP in the AIC, delete the AIC as well
            instance.aic.delete()
    except InformationPackage.DoesNotExist:
        pass


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
