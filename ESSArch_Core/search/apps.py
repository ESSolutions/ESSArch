from django.apps import AppConfig
from django.conf import settings
from elasticsearch_dsl.connections import connections


class SearchConfig(AppConfig):
    name = 'ESSArch_Core.search'
    verbose_name = 'Search'

    def ready(self):
        connections.configure(**settings.ELASTICSEARCH_CONNECTIONS)
