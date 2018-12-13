.. _epp-running:

*************************************
Running ESSArch Preservation Platform
*************************************


Start EPP server
================

.. note::
   A startup or shutdown of EPP should always be controlled

.. code-block:: shell

   # Please run the following command as user root
   $ systemctl start celerydepp
   $ systemctl start daphneepp
   $ systemctl start wsworkerepp
   $ systemctl start esshttpd

Stop EPP server
===============

.. code-block:: shell

   # Please run the following command as user root
   $ systemctl stop esshttpd
   $ systemctl stop celerydepp
   $ systemctl stop daphneepp
   $ systemctl stop wsworkerepp

Access EPP web user interface
=============================

Start your preferable web browser and connect to EPP Server name or IP address.

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
