.. _epp-upgrade:

*************************************
Upgrade ESSArch Preservation Platform
*************************************


Stop services
=============

* esshttpd
* celerydepp
* celerybeatepp
* daphneepp
* wsworkerepp
* rabbitmq-server
* redis
* elasticsearch

Verify that a backup of the database exists at /ESSArch/backup
==============================================================

Move old installation
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ cd /ESSArch
   $ mkdir old
   $ mv config install install*.log pd old/


Install new ESSArch Preservation Platform
=========================================

.. code-block:: shell

   $ su - arch
   [arch@server ~]$ tar xvf ESSArch_PP_installer-x.x.x.tar.gz
   [arch@server ~]$ cd ESSArch_PP_installer-x.x.x
   [arch@server ~]$ ./install

Collect static files to be served by apache httpd
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   [arch@server ~]$ python $EPP/manage.py collectstatic

Upgrade database schema
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   [arch@server ~]$ python $EPP/manage.py migrate

.. attention::

   When upgrading you must ensure that the storage engine is correct for the
   database. In MySQL the storage engine for previously created tables can be
   found by the following command::

      SELECT table_schema, table_name, engine FROM INFORMATION_SCHEMA.TABLES where table_schema = ”epp”;

   If you are not using the default storage engine (currently InnoDB) then it
   must be specified in your configuration file, e.g.::

      DATABASES = {
          'default': {
              'ENGINE': 'django.db.backends.mysql',
              'NAME': 'epp',
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

.. attention::

   Only use this default configuration for test purposes, do not install this
   default configuration in production. Replace XX with country specific profiles:
   se, no or eark

.. note::

   Before running the script, compare it with the data currently in the
   database and see if running it is necessary

.. code-block:: shell

   [arch@server ~]$ python $EPP/install/install_default_config_epp.py
   [arch@server ~]$ python $EPP/install/install_profiles_epp_XX.py
   [arch@server ~]$ python $EC/ESSArch_Core/install/install_default_config.py

For production/custom installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have made a custom configuration you should compare your configuration
with the new default configuration and see if there is anything new

.. note::

   Before running the script, compare it with the data currently in the
   database and see if running it is necessary

.. code-block:: shell

   [arch@server ~]$ diff $EPP/extra/install_config.py /home/arch/install_config_custom.py

If there is anything new in the default you should copy this to your custom installation file and install it

.. code-block:: shell

   [arch@server ~]$ cp $EPP/install_default_config_epp.py /home/arch/install_config_custom.py
   [arch@server ~]$ python /home/arch/install_config_custom.py

Compare and restore configuration files at /ESSArch/config from old directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ diff -qr /ESSArch/config old

Start services
==============

* celerydepp
* celerybeatepp
* daphneepp
* wsworkerepp
* rabbitmq-server
* redis
* elasticsearch
* esshttpd
