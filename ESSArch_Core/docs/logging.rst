.. _etp-external-logging:

**********************************
External logging and monitoring
**********************************


Using the ELK stack
===================

The Elastic-Logstash-Kibana (ELK) stack can be used to store and monitor logs
from ESSArch.


Start by installing the necessary logstash dependencies:

.. code-block:: bash

    $ pip install -e /path/to/ESSArch_Core/[logstash]


If ESSArch is installed using docker, then the complete ELK-stack is started
together with ESSArch:

.. code-block:: bash

    $ docker-compose up -d

When the first log is sent from the application to logstash, you will get
the option to create an index in Kibana.

By default the index pattern should be::

    logstash-*


Click next to create the index pattern, and then head over to `Discover` page
to see your logs.


Logstash Configuration
^^^^^^^^^^^^^^^^^^^^^^

Example ``logstash.conf``::

    input {
        tcp {
            port => 5000
            codec => json
        }
    }

    filter {
        json {
            source => "[message][raw]"
        }

        # Workaround for HTTP logs created from "django.channels.server" that have an extra "\u001b[m" at start and "\u001b[0m" at end.
        if [type] == "django_http" {
            grok {
                match => { "message" => "m%{URIPROTO:protocol} %{WORD:method} %{URIPATHPARAM:request} %{NUMBER:status_code} \[%{NUMBER:duration}, %{HOSTPORT:host}\]" }
            }
            mutate {
                remove_field => [ "message" ]
            }
        }
    }

    output {
        elasticsearch {
            hosts => "elasticsearch:9200"
        }
    }


Configuration
^^^^^^^^^^^^^

Modify your ESSArch settings by adding the logstash handlers and loggers. This
will override the default LOGGING configurations.

This is an example for ETP:

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
                'application': 'ETP',
                'environment': 'dev'
            }
        },
        'logstash_http': {
            '()': 'logstash_async.formatter.DjangoLogstashFormatter',
            'message_type': 'django_http',
            'fqdn': False,
            'extra_prefix': '',
            'extra': {
                'application': 'ETP',
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
            'ssl_enable': True,
            'ssl_verify': True,
            'ca_certs': 'etc/ssl/certs/logstash_ca.crt',
            'certfile': '/etc/ssl/certs/logstash.crt',
            'keyfile': '/etc/ssl/private/logstash.key',
            'database_path': '{}/etp_logstash_http.db'.format('/var/tmp'),
        },
        'logstash': {
            'level': 'INFO',
            'class': 'logstash_async.handler.AsynchronousLogstashHandler',
            'formatter': 'logstash',
            'transport': 'logstash_async.transport.TcpTransport',
            'host': 'localhost',
            'port': 5000,
            'ssl_enable': True,
            'ssl_verify': True,
            'ca_certs': 'etc/ssl/certs/logstash_ca.crt',
            'certfile': '/etc/ssl/certs/logstash.crt',
            'keyfile': '/etc/ssl/private/logstash.key',
            'database_path': '{}/etp_logstash.db'.format('/var/tmp'),
        },
    },

    'loggers': {
        ...
        'essarch': {
            'handlers': ['core', 'file_etp', 'logstash'],
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
documentation for the logstash python library:
https://python-logstash-async.readthedocs.io/en/stable/usage.html#usage-with-django

.. seealso::

    :ref:`configuration`
