.. _development-environment:

************************
 Development Environment
************************


Getting the source
==================

To get started, clone the repositories:

.. code-block:: bash

    $ git clone https://github.com/ESSolutions/ESSArch_Core
    $ git clone https://github.com/ESSolutions/ESSArch_Tools_Producer
    $ git clone https://github.com/ESSolutions/ESSArch_Tools_Archive
    $ git clone https://github.com/ESSolutions/ESSArch_EPP

Setting up virtual Python environments
======================================

You will need Python 3.6 along with ``pip``, which is what the backend of
ESSArch is built on. It is recommended to have ESSArch in its own virtual
python environment. Taking it even further, one might also have one virtual
environment for each ESSArch application.

Creating and managing virtual environments can be done with the virtualenv_
Python package or using more advanced tools such as pyenv_ or pipenv_.


Installing Python dependencies
==============================

Inside each virtual environment you then need to install the Python
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

Each application backend requires the path to the ESSArch Core directory along
with the application directory to be included in the ``PYTHONPATH`` variable.
Each application frontend requires the ``ÈC_FRONTEND`` variable to be set to
the absolute path of the ``ESSArch_Core/frontend`` directory in ESSArch Core.

If you have a config and/or plugin directory, these will also have to be added
to the ``PYTHONPATH`` variable.


Here is an example for an installation of ESSArch Tools for Producer:

.. code-block:: bash

    export EC=$HOME/git/core
    export EC_FRONTEND=$EC/ESSArch_Core/frontend
    export ETP=$HOME/git/etp/ESSArch_TP
    export PYTHONPATH=$ETP:$EC:/ESSArch/config/:/ESSArch/plugins


.. tip::

    Tools such as direnv_ are recommended to automatically switch between
    environment variables while working with multiple applications.


Configuring services
====================

ESSArch requires a relational database, RabbitMQ, Redis and Elasticsearch. Each
service can be configured in the configuration file of each application.

.. seealso::

    :ref:`configuration`


Running migrations
==================

All changes to the database are applied using the `migrate` command:

.. code-block:: bash

    $ python manage.py migrate

Installing initial data
=======================

Use the installation script in ESSArch Core to setup default event types and
system parameters

.. code-block:: bash

    $ python ${EC}/ESSArch_Core/install/install_default_config.py

The installation script in each application adds users, paths and other
application specific initial data.

.. code-block:: bash

    $ python install/install_default_config_{app}.py

.. important::

    The paths created has to exist in the filesystem before being used. See
    :ref:`directory-structure` for the default structure


Building the frontend
=====================

To build the frontend you need Node.js_ 8+ with yarn_, and gulp-cli_ globally
installed:

.. code-block:: bash

    $ yarn global add gulp-cli

For each application, install the dependencies and build the source:

.. code-block:: bash

    $ cd frontend/static/frontend
    $ yarn
    $ gulp


Starting the development web server
===================================

To start the development web server provided by Django for the applications,
run the following in the root of each application:

.. code-block:: bash

    $ python manage.py runserver


To run multiple applications simultaneously you need to start each on different
ports, simply append the port to the end of the
command:

.. code-block:: bash

    $ python manage.py runserver 8000


You can now access the application from your web browser by visiting
http://localhost:8000/

Starting background workers
===========================

Much of ESSArch is done on background workers. These needs to run in addition
to the web server. Run the following in the root of each application:

.. code-block:: bash

    $ celery -A config worker --loglevel=info --concurrency=5 -Ofair -Q celery,validation,file_operation,io_disk,pollers


Starting background beat processes
==================================

Background beat processes are also needed to run some operations continously.
Run the following in the root of each application:

.. code-block:: bash

    $ celery -A config beat --loglevel=info

.. toctree::
    :maxdepth: 2

    prerequisites
    prepare_environment
    install
    upgrade
    safety_backup_procedures
    logfiles

.. _virtualenv: https://virtualenv.pypa.io/
.. _pyenv: https://github.com/pyenv/pyenv/
.. _pipenv: https://docs.pipenv.org/
.. _direnv: https://direnv.net/

.. _jsonfield: https://pypi.org/project/jsonfield/
.. _django-jsonfield: https://pypi.org/project/django-jsonfield/
.. _django-groups-manager: https://pypi.org/project/django-groups-manager/

.. _yarn: https://yarnpkg.com/
.. _gulp-cli: https://www.npmjs.com/package/gulp-cli/
.. _Node.js: https://nodejs.org/
