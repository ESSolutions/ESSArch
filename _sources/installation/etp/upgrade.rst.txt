.. _etp-upgrade:

******************************
Upgrade ESSArch Tools Producer
******************************


Stop services
=============

* esshttpd
* celerydetp
* celerybeatetp
* daphneetp
* wsworkeretp
* rabbitmq-server
* redis

Verify that a backup of the database exists at /ESSArch/backup
==============================================================

Move old installation
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ cd /ESSArch
   $ mkdir old
   $ mv config install install*.log pd old/


Install new ESSArch Tools Producer
==================================

.. code-block:: shell

   $ su - arch
   [arch@server ~]$ tar xvf ESSArch_TP_installer-x.x.x.tar.gz
   [arch@server ~]$ cd ESSArch_TP_installer-x.x.x
   [arch@server ~]$ ./install

Collect static files to be served by apache httpd
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   [arch@server ~]$ python $ETP/manage.py collectstatic

Upgrade database schema
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   [arch@server ~]$ python $ETP/manage.py migrate

.. attention::

   When upgrading you must ensure that the storage engine is correct for the
   database. In MySQL the storage engine for previously created tables can be
   found by the following command::

      SELECT table_schema, table_name, engine FROM INFORMATION_SCHEMA.TABLES where table_schema = ”etp”;

   If you are not using the default storage engine (currently InnoDB) then it
   must be specified in your configuration file, e.g.::

      DATABASES = {
          'default': {
              'ENGINE': 'django.db.backends.mysql',
              'NAME': 'etp',
              'USER': 'arkiv',
              'PASSWORD': 'password',
              'HOST': '',
              'PORT': '',
              'OPTIONS': {
                 #"init_command": "SET storage_engine=MyISAM",  # MySQL (<= 5.5.2)
                 "init_command": "SET default_storage_engine=MyISAM",  # MySQL (>= 5.5.3)
              }
          }
      }

Add default configuration data to database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

   Before running the script, compare it with the data currently in the
   database and see if running it is necessary

.. code-block:: shell

   [arch@server ~]$ python $ETP/install/install_default_config_etp.py

Compare and restore configuration files at /ESSArch/config from old directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ diff -qr /ESSArch/config old

Start services
==============

* celerydetp
* celerybeatetp
* daphneetp
* wsworkeretp
* rabbitmq-server
* redis
* esshttpd
