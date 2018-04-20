from django.conf import settings

from elasticsearch_dsl.connections import connections

DEFAULT_MAX_RESULT_WINDOW = 10000
ELASTICSEARCH_REQUEST_TIMEOUT = getattr(settings, 'ELASTICSEARCH_REQUEST_TIMEOUT', 60)


def connect(alias='default'):
    return connections.create_connection(alias, timeout=ELASTICSEARCH_REQUEST_TIMEOUT)


def get_connection(alias='default'):
    try:
        return connections.get_connection(alias)
    except:
        return connect(alias)

get_connection()
