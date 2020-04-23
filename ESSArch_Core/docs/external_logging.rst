.. _external-logging:

**********************************
External logging and monitoring
**********************************


Using the Elastic Stack
=======================

The Elastic Stack can be used to store and monitor logs
from ESSArch.


Start by installing the necessary Logstash dependencies:

.. code-block:: bash

    $ pip install -e /path/to/ESSArch_Core/[logstash]

Configuration
^^^^^^^^^^^^^

Modify your ESSArch settings by adding the Logstash handlers and loggers. This
will override the default LOGGING configurations.

For example:

.. code-block:: python

  LOGGING = {
    ...
    'formatters': {
        ...
        'logstash': {
            '()': 'logstash_async.formatter.DjangoLogstashFormatter',
            'message_type': 'logstash',
            'fqdn': False,
            'extra_prefix': '',
            'extra': {
                'application': 'ESSArch',
                'environment': 'dev'
            }
        },
        'logstash_http': {
            '()': 'logstash_async.formatter.DjangoLogstashFormatter',
            'message_type': 'django_http',
            'fqdn': False,
            'extra_prefix': '',
            'extra': {
                'application': 'ESSArch',
                'environment': 'dev'
            }
        },
    },
    'handlers': {
        ...
        'logstash_http': {
            'level': 'INFO',
            'class': 'logstash_async.handler.AsynchronousLogstashHandler',
            'formatter': 'logstash_http',
            'transport': 'logstash_async.transport.TcpTransport',
            'host': 'localhost',
            'port': 5000,
            'ssl_enable': False,
            'ssl_verify': False,
            'database_path': '{}/logstash_http.db'.format('/var/tmp'),
        },
        'logstash': {
            'level': 'INFO',
            'class': 'logstash_async.handler.AsynchronousLogstashHandler',
            'formatter': 'logstash',
            'transport': 'logstash_async.transport.TcpTransport',
            'host': 'localhost',
            'port': 5000,
            'ssl_enable': False,
            'ssl_verify': False,
            'database_path': '{}/logstash.db'.format('/var/tmp'),
        },
    },

    'loggers': {
        ...
        'essarch': {
            'handlers': ['core', 'file_essarch', 'logstash'],
            'level': 'DEBUG',
        },
        'essarch.auth': {
            'level': 'INFO',
            'handlers': ['log_file_auth', 'logstash'],
            'propagate': False,
        },
        'django': {
            'handlers': ['logstash'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['logstash'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['logstash'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.channels.server': {
            'handlers': ['logstash_http'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.contrib.auth': {
            'handlers': ['logstash'],
            'level': 'INFO',
            'propagate': False,
        },
  }


More information on how to configure the logging can be found in the
documentation for the Logstash Python library:
https://python-logstash-async.readthedocs.io/en/stable/usage.html#usage-with-django

Using Docker
^^^^^^^^^^^^^

If ESSArch is installed using Docker, then the complete Elastic Stack is started
together with ESSArch:

.. code-block:: bash

    $ docker-compose up -d

However, to have ESSArch write to logstash you need to update your
ESSArch settings as described above, remember to change the log handler host from
localhost to logstash. A default ``logstash.conf`` is already
configured and does not need to be updated.

Viewing logs in Kibana
^^^^^^^^^^^^^^^^^^^^^^

When the first log is sent from the application to Elasticsearch using
Logstash, you will get the option to create an index in Kibana.

By default the index pattern should be::

    logstash-*


Click next to create the index pattern, and then head over to the `Discover`
page to see your logs.


.. seealso::

    :ref:`configuration`
