import errno
import shutil

from django.db.models.signals import post_delete
from django.dispatch import receiver
from ESSArch_Core.ip.models import Workarea


@receiver(post_delete, sender=Workarea)
def workarea_post_delete(sender, instance, using, **kwargs):
    try:
        shutil.rmtree(instance.path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    try:
        instance.processstep.clear_cache()
    except AttributeError:
        pass
