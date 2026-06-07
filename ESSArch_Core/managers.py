from django.db import models

from ESSArch_Core.auth.util import get_objects_for_user


class OrganizationQuerySet(models.QuerySet):
    def for_user(self, user, perms=None):
        return get_objects_for_user(user, self, perms)


class OrganizationManager(models.Manager):
    def get_queryset(self):
        return OrganizationQuerySet(self.model, using=self._db)

    def for_user(self, user, perms=None, include_all_groups=False):
        """
        Returns objects for which a given ``users`` groups in the
        ``users`` current organization has all permissions in ``perms``

        :param user: ``User`` instance for which objects would be
        returned
        :param perms: single permission string, or sequence of permission
        strings which should be checked
        """
        if include_all_groups:
            current_organization = False
        else:
            current_organization = True

        return get_objects_for_user(user, self.model, perms, current_organization=current_organization)
