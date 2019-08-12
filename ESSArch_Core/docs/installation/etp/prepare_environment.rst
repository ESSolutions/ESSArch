.. _etp-prepare-environment:

*******************
Prepare Environment
*******************


Customize user environment for arch user
========================================

Add the following rows to ``/home/arch/.bash_profile`` after “ESSArch Core” section:

.. code-block:: shell

   ### ETP start
   ##
   export ETP=/ESSArch/pd/python/lib/python3.7/site-packages/ESSArch_TP
   export PYTHONPATH=$ETP:$EC_PYTHONPATH
   alias env_etp='export PYTHONPATH=$ETP:$EC_PYTHONPATH;cd $ETP'
   ##
   ### ETP end

.. note::

   If you install multiple ESSArch products such as ETP, ETA or EPP on the
   same server, you must adapt PYTHONPATH so that only one product is used at a
   time. As an alternative, you can run the alias env_etp, env_eta or env_epp
   that configure PYTHONPATH for each product before you is performing
   operations.
