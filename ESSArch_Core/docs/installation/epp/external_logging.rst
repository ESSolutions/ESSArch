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
            'propagate': True,
        },
        'django.security': {
            'handlers': ['logstash'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.channels.server': {
            'handlers': ['logstash'],
            'level': 'INFO',
            'propagate': True,
        },
  }
