.. _epp-prepare-environment:

*******************
Prepare Environment
*******************


Customize user environment for arch user
========================================

Add the following rows to ``/home/arch/.bash_profile`` after “ESSArch Core” section:

.. code-block:: shell

   ### EPP start
   ##
   export EPP=/ESSArch/pd/python/lib/python3.6/site-packages/ESSArch_PP
   export PYTHONPATH=$EPP:$EC_PYTHONPATH
   alias env_epp='export PYTHONPATH=$EPP:$EC_PYTHONPATH;cd $EPP'
   ##
   ### EPP end

.. note::

   If you install multiple ESSArch products such as ETP, ETA or EPP on the
   same server, you must adapt PYTHONPATH so that only one product is used at a
   time. As an alternative, you can run the alias env_epp, env_eta or env_epp
   that configure PYTHONPATH for each product before you is performing
   operations.
