.. _etp-running:

******************************
Running ESSArch Tools Producer
******************************


Start ETP server
================

.. note::
   A startup or shutdown of ETP should always be controlled

.. code-block:: shell

   # Please run the following command as user root
   $ systemctl start celerydetp
   $ systemctl start daphneetp
   $ systemctl start wsworkeretp
   $ systemctl start esshttpd

Stop ETP server
===============

.. code-block:: shell

   # Please run the following command as user root
   $ systemctl stop esshttpd
   $ systemctl stop celerydetp
   $ systemctl stop daphneetp
   $ systemctl stop wsworkeretp

Access ETP web user interface
=============================

Start your preferable web browser and connect to ETP Server name or IP address.

By default, for test purpose, the installation has configured the following
users:

+--------------+--------------+-------------------------+
| **Username** | **Password** | **Role/Permissions**    |
+==============+==============+=========================+
| user         | user         | prepare, create, submit |
+--------------+--------------+-------------------------+
| admin        | admin        | admin                   |
+--------------+--------------+-------------------------+
| sysadmin     | sysadmin     | sysadmin                |
+--------------+--------------+-------------------------+
