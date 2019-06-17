.. _core-prepare-environment:

*******************
Prepare Environment
*******************


Create user and group
=====================

.. code-block:: shell

   #Please run the following command as user root.

   $ groupadd arch
   $ useradd -c "ESSArch System Account" -m -g arch arch


Set password for arch user
==========================

.. code-block:: shell

   # Please run the following command as user root.

   $ passwd arch
   Changing password for user arch.
   New UNIX password: password
   Retype new UNIX password: password

Customize user environment for arch user
========================================

Add the following rows to ``/home/arch/.bash_profile`` :

.. code-block:: shell

   ### ESSArch Core start
   ##
   export PATH=/ESSArch/pd/python/bin:/ESSArch/pd/libxml/bin:/ESSArch/pd/libxslt/bin:$PATH:/usr/sbin
   export LANG=en_US.UTF-8
   export LD_LIBRARY_PATH=/ESSArch/pd/python/lib:/ESSArch/pd/libxslt/lib:/ESSArch/pd/libxml/lib:$LD_LIBRARY_PATH
   export EC=/ESSArch/pd/python/lib/python3.6/site-packages
   export EC_PYTHONPATH=$EC:/ESSArch/config
   export PYTHONPATH=$EC_PYTHONPATH
   export DJANGO_SETTINGS_MODULE=ESSArch_Core.config.settings
   alias log='cd /ESSArch/log'
   ##
   ### ESSArch Core end

Create installation directory
=============================

.. code-block:: shell

   # Please run the following command as user root.

   $ mkdir /ESSArch
   $ chown -R arch:arch /ESSArch
