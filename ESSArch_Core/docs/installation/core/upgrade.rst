.. _core-upgrade:

********************
Upgrade ESSArch Core
********************


Stop services
=============

* esshttpd
* celerydepp
* celerybeatepp
* celerydeta
* celerybeateta
* celerydetp
* celerybeatetp
* daphneepp
* daphneeta
* daphneetp
* wsworkerepp
* wsworkereta
* wsworkeretp

Verify that a backup of the database exists at /ESSArch/backup
==============================================================

Move old installation
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ cd /ESSArch
   $ mkdir old
   $ mv config install install*.log pd old/


Install new ESSArch Core
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ su - arch
   [arch@server ~]$ tar xvf ESSArch_Core_installer-x.x.x.tar.gz
   [arch@server ~]$ cd ESSArch_Core_installer-x.x.x
   [arch@server ~]$ ./install

Compare and restore configuration files at /ESSArch/config from old directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: shell

   $ diff -qr /ESSArch/config old

Start services
==============

* celerydepp
* celerybeatepp
* celerydeta
* celerybeateta
* celerydetp
* celerybeatetp
* daphneepp
* daphneeta
* daphneetp
* wsworkerepp
* wsworkereta
* wsworkeretp
* esshttpd
