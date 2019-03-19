.. _epp-external-logging:

**********************************
Externalize logging and monitoring
**********************************


Elastic-stack
=============

Install the logstash plugin

.. code-block:: bash

    $ pip install -e /path/to/ESSArch_Core/[logstash]


Start Elastic-stack
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    $ cd docker/epp
    $ docker-compose up -d

Then navigate to http://localhost:5603 to open up Kibana.
*After* the first log is sent from the application to logstash, you will get the option to create an index in http://localhost:5603/app/kibana#/management/kibana/index

Per default the index pattern should be::

    logstash-*


Click next to create the index pattern, and then head over to `Discover` page to see your logs: http://localhost:5603/app/kibana#/discover


LogStash Configuration
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

Modify your ``local_epp_settings.py`` by adding the logstash handlers and loggers. This will override the default LOGGING configurations.

.. code-block:: python

  LOGGING = {
    ...
    'handlers': {
        ...
        'logstash': {
            'level': 'DEBUG',
            'class': 'logstash.TCPLogstashHandler',
            'host': 'localhost',  # logstash host
            'port': 5003,  # logstash port
            'version': 1,
            'message_type': 'django',
            'fqdn': False,
            'tags': ['EPP'],  # Name of the app
        },
        'logstash_http': {  # This handler is for distinguishing http requests
            'level': 'INFO',
            'class': 'logstash.TCPLogstashHandler',
            'host': 'localhost',  # logstash host
            'port': 5003,  # logstash port
            'version': 1,
            'message_type': 'django_http',
            'fqdn': False,
            'tags': ['EPP'],  # Name of the app
        },
    },

    'loggers': {
        ...
        'essarch': {
            'handlers': ['core', 'file_epp', 'logstash'],
            'level': 'DEBUG',
        },
        'essarch.auth': {
            'level': 'DEBUG',
            'handlers': ['log_file_auth', 'logstash'],
            'propagate': False,
        },
        'django.request': {
            'handlers': ['logstash'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['logstash'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.channels.server': {
            'handlers': ['logstash_http'],
            'level': 'INFO',
            'propagate': False,
        },
  }
