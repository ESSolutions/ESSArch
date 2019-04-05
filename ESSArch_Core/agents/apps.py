from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AgentsConfig(AppConfig):
    name = 'ESSArch_Core.agents'
    verbose_name = _('Agents')
