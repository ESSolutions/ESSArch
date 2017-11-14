from elasticsearch_dsl.connections import connections

DEFAULT_MAX_RESULT_WINDOW = 10000


def connect(alias='default'):
    connections.create_connection(alias)


def get_connection(alias='default'):
    try:
        connections.get_connection(alias)
    except:
        connect(alias)
