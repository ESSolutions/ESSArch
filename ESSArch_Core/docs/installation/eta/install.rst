.. _eta-install:

******************************
Install ESSArch Tools Archive
******************************


ETA installation script
=======================

Please download the latest installation package from `Github <https://github.com/ESSolutions/ESSArch_Tools_Archive/releases/latest>`_

.. code-block:: shell

   # Change to user "arch" with the following command.
   $ su - arch

   # Extract and install the downloaded package.
   [arch@server ~]$ tar xvf ESSArch_TA_installer-x.x.x.tar.gz
   [arch@server ~]$ cd ESSArch_TA_installer-x.x.x
   [arch@server ~]$ ./install

   # The installation of ESSArch is now running and dependent on hardware
   # configuration, the installation may take some time. To see details of the
   # installation progress please start a new terminal window and run the
   # following command.
   [arch@server ~]$ tail -f /ESSArch/install_eta.log

   # When installation is finished, search in the log file /ESSArch/install_eta.log
   # for any unexpected errors indicating failure of installation of any modules.

Configuration
=============

Apache httpd configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

Edit file ``/ESSArch/config/httpd-eta.conf`` and change the configuration entry
for "ServerName" to same as the hostname of the ESSArch server.

Add the line ``"Include /ESSArch/config/httpd-eta.conf"`` in the file
``/ESSArch/config/httpd.conf``

For test purpose you can use the existing configuration for SSL certificate,
but for production environment and for maximum security we recommend generating
your own SSL certificate or if you have your own SSL trusted certificate
install them in the apache httpd configuration.

Collect static files to be served by apache httpd
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user arch
   [arch@server ~]$ python $ETA/manage.py collectstatic


ETA configuration
^^^^^^^^^^^^^^^^^

``/ESSArch/config`` contains the configuration files for ESSArch. To change the
configuration of ETA, create or update
``/ESSArch/config/local_eta_settings.py``

RabbitMQ virtual host configuration for ETA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   Add virtual host to RabbitMQ as user root:
   $ rabbitmqctl add_user guest guest
   $ rabbitmqctl add_vhost eta
   $ rabbitmqctl set_permissions -p eta guest ".*" ".*" ".*"

Database
========

ESSArch is designed to be RDBMS-independent. However the installation package
is prepared for MySQL/MariaDB and the following instructions assume that you
use MySQL/MariaDB.

MySQL
^^^^^
Follow the instructions below in order to create the user and tables required by ETA installation.

.. code-block:: shell

   # To enable MySQL on CentOS 6 run the following commands as user root
   $ /sbin/chkconfig mysqld on
   $ /sbin/service mysqld start
   $ /usr/bin/mysql_secure_installation

   # The MySQL commands listed below can be run within the mysql program, which
   # may be invoked as follows.
   $ mysql -u root -p

   # Create the database. For example, to create a database named "eta", enter.
   $ mysql> CREATE DATABASE eta DEFAULT CHARACTER SET utf8;

   # Set username, password and permissions for the database. For example, to
   # set the permissions for user "arkiv" with password "password" on database
   # "eta", enter:
   $ mysql> GRANT ALL ON eta.* TO arkiv@localhost IDENTIFIED BY 'password';

MariaDB
^^^^^^^
Follow the instructions below in order to create the user and tables required by ETA installation.

.. code-block:: shell

   # To enable MariaDB on CentOS 7 run the following commands as user: root.
   $ /sbin/chkconfig mariadb on
   $ /sbin/service mariadb start
   $ /usr/bin/mysql_secure_installation

   # The MySQL commands listed below can be run within the mysql program, which
   # may be invoked as follows.
   $ mysql -u root -p

   # Create the database. For example, to create a database named "eta", enter.
   $ mysql> CREATE DATABASE eta DEFAULT CHARACTER SET utf8;

   # Set username, password and permissions for the database. For example, to
   # set the permissions for user "arkiv" with password "password" on
   # database "eta", enter:
   $ mysql> GRANT ALL ON eta.* TO arkiv@localhost IDENTIFIED BY 'password';

Create default tables in database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user arch
   [arch@server ~]$ python $ETA/manage.py migrate

Add default configuration data to database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user arch
   [arch@server ~]$ python $ETA/install/install_default_config_eta.py
   [arch@server ~]$ python $EC/ESSArch_Core/install/install_default_config.py

Enable automatic startup at system boot
=======================================

.. code-block:: shell

   # Login as root user and set ETA path variable
   $ export ETA_package='ESSArch_TA_installer-1.2.0'

Enable workerprocess
====================

.. code-block:: shell

   # Please run the following commands as user root
   $ cp /home/arch/${ETA_package}/extra/celerydeta.service /usr/lib/systemd/system/
   $ systemctl enable celerydeta.service
   $ cp /home/arch/${ETA_package}/extra/celerybeateta.service /usr/lib/systemd/system/
   $ systemctl enable celerybeateta.service
   $ cp /home/arch/${ETA_package}/extra/daphneeta.service /usr/lib/systemd/system/
   $ systemctl enable daphneeta.service
   $ cp /home/arch/${ETA_package}/extra/wsworkereta.service /usr/lib/systemd/system/
   $ systemctl enable wsworkereta.service
