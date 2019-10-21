.. _core-prerequisites:

*************
Prerequisites
*************

.. attention::

   Hardware configuration for server, network and storage architecture is not
   affected in this guide. Software configurations for server operating systems
   occur preferably before the installation of ESSArch begins. The installation
   is expected to be done as user 'root'.


Supported OS platforms
======================

+------------------------------+-------------------+
| **OS**                       | **Version**       |
+==============================+===================+
| CentOS / Redhat              | 7 (x86\_64)       |
+------------------------------+-------------------+
| CentOS / Redhat              | 8 (x86\_64)       |
+------------------------------+-------------------+
| SUSE Linux Enterprise Server | 15 (x86\_64)      |
+------------------------------+-------------------+
| Windows Server               | 2016 (x86\_64)    |
+------------------------------+-------------------+

(Other operating systems have been tested but are not yet
fully supported, please send us a request with your needs)


Database
========

+-------------------------------------------------------+-----------------+
| Database                                              | Minimum Version |
+=======================================================+=================+
| `PostgreSQL <https://www.postgresql.org>`_            | 9.4             |
+-------------------------------------------------------+-----------------+
| `MySQL <https://www.mysql.com>`_                      | 5.6             |
+-------------------------------------------------------+-----------------+
| `MariaDB <https://mariadb.org>`_                      | 10.1            |
+-------------------------------------------------------+-----------------+
| `SQL Server <https://www.microsoft.com/sql-server>`_  | 2008            |
+-------------------------------------------------------+-----------------+
| `SQLite <https://www.sqlite.org>`_                    | 3.8.3           |
+-------------------------------------------------------+-----------------+


`Redis <https://redis.io>`_ (Minimum version: 3.0)
==================================================

ESSArch uses Redis as a cache to improve performance and to support real-time
notifications.

Docker image: https://hub.docker.com/_/redis/.

To install on Windows, see https://github.com/microsoftarchive/redis


`RabbitMQ <https://www.rabbitmq.com>`_ (Minimum version: 3.7.0)
===============================================================

RabbitMQ is used for the workflow management and distribution in ESSArch.

Docker image: https://hub.docker.com/_/rabbitmq/


`Elasticsearch <https://www.elastic.co/products/elasticsearch>`_ (Supported version: 6.5.x)
===========================================================================================

Elasticsearch is the search engine used in ESSArch.

Docker image: https://www.docker.elastic.co/

The `Ingest Attachment Processer Plugin
<https://www.elastic.co/guide/en/elasticsearch/plugins/current/ingest-attachment.html>`_
is also required inorder to store and later search file contents.
