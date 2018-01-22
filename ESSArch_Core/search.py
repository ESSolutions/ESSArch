from elasticsearch_dsl.connections import connections

DEFAULT_MAX_RESULT_WINDOW = 10000


def connect(alias='default'):
    return connections.create_connection(alias)


def get_connection(alias='default'):
    try:
        return connections.get_connection(alias)
    except:
        return connect(alias)
