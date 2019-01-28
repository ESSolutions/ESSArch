.. _directory-structure:

Directory Structure
===================


This the default structure of the data directories. Administrators can change
these paths using the administration interface.


.. code-block:: txt

    /ESSArch/data/
    ├── epp
    │   ├── access
    │   ├── cache
    │   ├── disseminations
    │   ├── ingest
    │   ├── orders
    │   ├── reports
    │   │   ├── appraisal
    │   │   └── conversion
    │   ├── temp
    │   ├── work
    │   └── workarea
    ├── eta
    │   ├── reception
    │   │   └── eft
    │   ├── uip
    │   └── work
    │       └── admin
    ├── etp
    │   ├── prepare
    │   ├── prepare_reception
    │   └── reception
    ├── gate
    │   └── reception
    ├── receipts
    │   └── xml
    ├── remote
    └── store
        ├── disk1
        └── longterm_disk1
