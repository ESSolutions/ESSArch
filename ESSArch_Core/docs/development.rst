.. _development-environment:

************************
 Development Environment
************************


Getting the source
==================

To get started, clone the repository:

.. code-block:: bash

    $ git clone https://github.com/ESSolutions/ESSArch

Setting up virtual Python environments
======================================

You will need Python 3.7 along with ``pip``, which is what the backend of
ESSArch is built on. It is recommended to have ESSArch in its own virtual
python environment.

Creating and managing virtual environments can be done with the virtualenv_
Python package or using more advanced tools such as pyenv_ or pipenv_.


Installing Python dependencies
==============================

Run the following to install ESSArch and its Python
dependencies:

.. code-block:: bash

    $ cd ESSArch_Core
    $ pip install -e .

ESSArch Core also contains a number of extra dependencies depending on the
needs of the target environment. These are listed in the ``extras_require``
section of the ``setup.py`` file at the root of the directory and are installed
by appending a list of extras to the command above.

For example, to install the requirements for building the docs and running the
tests:

.. code-block:: bash

    $ cd ESSArch_Core
    $ pip install -e .[docs,tests]

Setting environment variables
=============================

If you have a config and/or plugin directory, these will also have to be added
to the ``PYTHONPATH`` variable.

.. code-block:: bash

    export PYTHONPATH=$PYTHONPATH:/ESSArch/config/:/ESSArch/plugins

Configuring services
====================

ESSArch requires a relational database, RabbitMQ, Redis and Elasticsearch. Each
service can be configured in the configuration file.

.. seealso::

    :ref:`configuration`


Running migrations
==================

All changes to the database are applied using the `migrate` command:

.. code-block:: bash

    $ python manage.py migrate

Installing initial data
=======================

Use the installation script in ESSArch Core to setup the default configuration

.. code-block:: bash

    $ python ESSArch_Core/install/install_default_config.py

.. important::

    The paths created has to exist in the filesystem before being used. See
    :ref:`directory-structure` for the default structure


Building the frontend
=====================

To build the frontend you need Node.js_ LTS with yarn_ installed, Then to build:

.. code-block:: bash

    $ cd frontend/static/frontend
    $ yarn
    $ yarn build:dev


Starting the development web server
===================================

To start the development web server provided by Django,
run the following in the project root directory:

.. code-block:: bash

    $ python manage.py runserver

You can now access ESSArch from your web browser by visiting
http://localhost:8000/

Starting background workers
===========================

Much of the work in ESSArch is done using background workers. These needs to run in addition
to the web server. Run the following in the project root directory:

.. code-block:: bash

    $ essarch worker


Starting background beat processes
==================================

Background beat processes are also needed to run some operations continuously.
Run the following in the project root directory:

.. code-block:: bash

    $ essarch beat

.. _virtualenv: https://virtualenv.pypa.io/
.. _pyenv: https://github.com/pyenv/pyenv/
.. _pipenv: https://docs.pipenv.org/

.. _django-groups-manager: https://pypi.org/project/django-groups-manager/

.. _yarn: https://yarnpkg.com/
.. _Node.js: https://nodejs.org/
