from django.db import models

from ESSArch_Core.auth.util import get_objects_for_user


class OrganizationManager(models.Manager):
    def for_user(self, user, perms):
        """
        Returns objects for which a given ``users`` groups in the
        ``users`` current organization has all permissions in ``perms``

        :param user: ``User`` instance for which objects would be
        returned
        :param perms: single permission string, or sequence of permission
        strings which should be checked
        """

        return get_objects_for_user(user, self.model, perms)
