.. _eta-prepare-environment:

*******************
Prepare Environment
*******************


Customize user environment for arch user
========================================

Add the following rows to ``/home/arch/.bash_profile`` after “ESSArch Core” section:

.. code-block:: shell

   ### ETA start
   ##
   export ETA=/ESSArch/pd/python/lib/python3.6/site-packages/ESSArch_TA
   export PYTHONPATH=$ETA:$EC_PYTHONPATH
   alias env_eta='export PYTHONPATH=$ETA:$EC_PYTHONPATH;cd $ETA'
   ##
   ### ETA end

.. note::

   If you install multiple ESSArch products such as ETP, ETA or EPP on the
   same server, you must adapt PYTHONPATH so that only one product is used at a
   time. As an alternative, you can run the alias env_etp, env_eta or env_epp
   that configure PYTHONPATH for each product before you is performing
   operations.
