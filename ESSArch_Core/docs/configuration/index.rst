.. _configuration:

**************
 Configuration
**************


To configure the applications you need to create a local settings file that is available in your ``PYTHONPATH``. This file is named differently depending on the application

+---------------------------------+------------------------+
| **Application**                 | **File name**          |
+=================================+========================+
| ESSArch Tools for Producer      | local_etp_settings.py  |
+---------------------------------+------------------------+
| ESSArch Tools for Archive       | local_eta_settings.py  |
+---------------------------------+------------------------+
| ESSArch Preservation Platform   | local_epp_settings.py  |
+---------------------------------+------------------------+


.. toctree::
    :maxdepth: 2

    databases
    redis
    rabbitmq
    elasticsearch
    transformers
