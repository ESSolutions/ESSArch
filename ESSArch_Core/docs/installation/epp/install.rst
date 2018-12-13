.. _epp-install:

*************************************
Install ESSArch Preservation Platform
*************************************


EPP installation script
=======================

Please download the latest installation package from `Github <https://github.com/ESSolutions/ESSArch_EPP/releases/latest>`_

.. code-block:: shell

   # Change to user "arch" with the following command.
   $ su - arch

   # Extract and install the downloaded package.
   [arch@server ~]$ tar xvf ESSArch_PP_installer-x.x.x.tar.gz
   [arch@server ~]$ cd ESSArch_PP_installer-x.x.x
   [arch@server ~]$ ./install

   # The installation of ESSArch is now running and dependent on hardware
   # configuration, the installation may take some time. To see details of the
   # installation progress please start a new terminal window and run the
   # following command.
   [arch@server ~]$ tail -f /ESSArch/install_epp.log

   # When installation is finished, search in the log file /ESSArch/install_epp.log
   # for any unexpected errors indicating failure of installation of any modules.

Configuration
=============

Apache httpd configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Edit file ``/ESSArch/config/httpd-epp.conf`` and change the configuration entry
for "ServerName" to same as the hostname of the ESSArch server.

Add the line ``"Include /ESSArch/config/httpd-epp.conf"`` in the file
``/ESSArch/config/httpd.conf``

For test purpose you can use the existing configuration for SSL certificate,
but for production environment and for maximum security we recommend generating
your own SSL certificate or if you have your own SSL trusted certificate
install them in the apache httpd configuration.

Collect static files to be served by apache httpd
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user arch
   [arch@server ~]$ python $EPP/manage.py collectstatic


EPP configuration
^^^^^^^^^^^^^^^^^

``/ESSArch/config`` contains the configuration files for ESSArch. To change the
configuration of EPP, create or update
``/ESSArch/config/local_epp_settings.py``

RabbitMQ virtual host configuration for EPP
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   Add virtual host to RabbitMQ as user root:
   $ rabbitmqctl add_user guest guest
   $ rabbitmqctl add_vhost epp
   $ rabbitmqctl set_permissions -p epp guest ".*" ".*" ".*"

Database
========

ESSArch is designed to be RDBMS-independent. However the installation package
is prepared for MySQL/MariaDB and the following instructions assume that you
use MySQL/MariaDB.

MySQL
^^^^^
Follow the instructions below in order to create the user and tables required by EPP installation.

.. code-block:: shell

   # To enable MySQL on CentOS 6 run the following commands as user root
   $ /sbin/chkconfig mysqld on
   $ /sbin/service mysqld start
   $ /usr/bin/mysql_secure_installation

   # The MySQL commands listed below can be run within the mysql program, which
   # may be invoked as follows.
   $ mysql -u root -p

   # Create the database. For example, to create a database named "epp", enter.
   $ mysql> CREATE DATABASE epp DEFAULT CHARACTER SET utf8;

   # Set username, password and permissions for the database. For example, to
   # set the permissions for user "arkiv" with password "password" on database
   # "epp", enter:
   $ mysql> GRANT ALL ON epp.* TO arkiv@localhost IDENTIFIED BY 'password';

MariaDB
^^^^^^^
Follow the instructions below in order to create the user and tables required by EPP installation.

.. code-block:: shell

   # To enable MariaDB on CentOS 7 run the following commands as user: root.
   $ /sbin/chkconfig mariadb on
   $ /sbin/service mariadb start
   $ /usr/bin/mysql_secure_installation

   # The MySQL commands listed below can be run within the mysql program, which
   # may be invoked as follows.
   $ mysql -u root -p

   # Create the database. For example, to create a database named "epp", enter.
   $ mysql> CREATE DATABASE epp DEFAULT CHARACTER SET utf8;

   # Set username, password and permissions for the database. For example, to
   # set the permissions for user "arkiv" with password "password" on
   # database "epp", enter:
   $ mysql> GRANT ALL ON epp.* TO arkiv@localhost IDENTIFIED BY 'password';

Create default tables in database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user arch
   [arch@server ~]$ python $EPP/manage.py migrate

Add default configuration data to database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. attention::

   Only use this default configuration for test purposes, do not install this
   default configuration in production. Replace XX with country specific profiles:
   se, no or eark

.. code-block:: shell

   # Please run the following command as user arch
   [arch@server ~]$ python $EPP/install/install_default_config_epp.py
   [arch@server ~]$ python $EPP/install/install_profiles_epp_XX.py
   [arch@server ~]$ python $EC/ESSArch_Core/install/install_default_config.py


For production/custom installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For production environment you should first make a copy of this configuration file and update for example site_profile, site_name.

.. code-block:: shell

   [arch@server ~]$ cp $EPP/install/install_default_config_epp.py /home/arch/install_config_custom.py

Update and run ``/home/arch/install_config_custom.py``:

.. code-block:: shell

   [arch@server ~]$ python /home/arch/install_config_custom.py

Enable automatic startup at system boot
=======================================

.. code-block:: shell

   # Login as root user and set EPP path variable
   $ export EPP_package='ESSArch_PP_installer-3.0.0'

Enable workerprocess
====================

.. code-block:: shell

   # Please run the following commands as user root
   $ cp /home/arch/${EPP_package}/extra/celerydepp.service /usr/lib/systemd/system/
   $ systemctl enable celerydepp.service
   $ cp /home/arch/${EPP_package}/extra/celerybeatepp.service /usr/lib/systemd/system/
   $ systemctl enable celerybeatepp.service
   $ cp /home/arch/${EPP_package}/extra/daphneepp.service /usr/lib/systemd/system/
   $ systemctl enable daphneepp.service
   $ cp /home/arch/${EPP_package}/extra/wsworkerepp.service /usr/lib/systemd/system/
   $ systemctl enable wsworkerepp.service
