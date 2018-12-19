from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ProfileConfig(AppConfig):
    name = 'ESSArch_Core.profiles'
    verbose_name = _('Profiles')
