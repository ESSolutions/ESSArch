========
Database
========

ESSArch uses SQLite by default and can be configured to use any other database
supported by Django or its plugins. See the `Django database documentation`_ for more
information on how to configure the database.


Here is an example using MySQL:

.. code-block:: python

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'etp',
            'USER': 'arch',
            'PASSWORD': 'password',
            'HOST': '127.0.0.1',
            'PORT': '3306',
            'OPTIONS': {
                'isolation_level': 'read committed',
            }
        }
    }

.. _Django database documentation: https://docs.djangoproject.com/en/stable/ref/databases/
