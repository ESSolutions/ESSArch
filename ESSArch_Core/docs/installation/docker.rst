.. _installation-docker:

******
Docker
******


For testing, experimenting and development of ESSArch, Docker can be used to
more easily and quickly setup an environment on your own machine.


Dependencies
------------
 * `Docker <https://www.docker.com/>`_
 * `Docker Compose <https://docs.docker.com/compose/install/>`_


1. Start by cloning `ESSolutions/ESSArch <https://github.com/ESSolutions/ESSArch>`_

2. Enter the docker directory and start the services


.. warning::
    Elasticsearch requires ``vm.max_map_count`` to be at least 262144, see
    `Install Elasticsearch with Docker <https://www.elastic.co/guide/en/elasticsearch/reference/6.5/docker.html#docker-cli-run-prod-mode>`_
    for more information

.. code-block:: bash

    $ cd docker
    $ docker-compose up -d

3. Wait for the essarch service to start by examining the logs

.. code-block:: bash

    $ docker-compose logs -f essarch

4. Finally visit http://localhost:8000 in your browser
