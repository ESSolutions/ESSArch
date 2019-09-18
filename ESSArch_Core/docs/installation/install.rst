.. _core-install:

********************
Install ESSArch Core
********************


EC installation script
======================

Please download the latest installation package from `Github <https://github.com/ESSolutions/ESSArch_Core/releases/latest>`_

.. code-block:: shell

   # Change to user "arch" with the following command.
   $ su - arch

   # Extract and install the downloaded package.
   [arch@server ~]$ tar xvf ESSArch_Core_installer-x.x.x.tar.gz
   [arch@server ~]$ cd ESSArch_Core_installer-x.x.x
   [arch@server ~]$ ./install

   # The installation of ESSArch is now running and dependent on hardware
   # configuration, the installation may take some time. To see details of the
   # installation progress please start a new terminal window and run the
   # following command.
   [arch@server ~]$ tail -f /ESSArch/install.log

   # When the installation is finished, search in the log file /ESSArch/install.log
   # for any unexpected errors indicating failure of installation of any modules.


Enable automatic startup at system boot
=======================================

.. code-block:: shell

   # Login as root user and set EC variables:
   $ export EC_package='ESSArch_Core_installer-1.1.0'

Enable automatic startup of Apache HTTPD
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user root.
   $ cp /home/arch/${EC_package}/extra/esshttpd.service /usr/lib/systemd/system/
   $ systemctl enable esshttpd.service

Enable automatic startup of RabbitMQ
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user root.
   $ systemctl enable rabbitmq-server.service
   $ systemctl start rabbitmq-server


Enable automatic backup of MySQL/MariaDB
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   # Please run the following command as user root.
   $ cp /ESSArch/config/automysqlbackup/runmysqlbackup /etc/cron.daily/runmysqlbackup
   $ chmod 744 /etc/cron.daily/runmysqlbackup
