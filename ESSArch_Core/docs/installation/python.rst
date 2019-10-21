.. _installation-python:

******
Python
******


Dependencies
------------
 * `Python 3.7 <https://www.python.org/>`_
 * `pip 18.0 or higher <https://pip.pypa.io/>`_

.. note::

    If you are not installing ESSArch on a dedicated machine it is recommended
    that you first create a virtual python environment.

    https://virtualenv.pypa.io


Install ESSArch
---------------

To install ESSArch and its dependencies, run

.. code-block:: bash

    $ pip install essarch


Once installed, you can run the `essarch` command to verify that
it has installed correctly.


.. code-block:: bash

    $ essarch


Configuring ESSArch
-------------------

ESSArch has a default configuration built-in which can be overridden in your
own local settings file.

Generate the local settings file using the following command and follow the
prompts:

.. code-block:: bash

    $ essarch settings generate

When the configuration is complete you need to setup the database tables
and load initial data:

.. code-block:: bash


    $ essarch install


Starting the built-in webserver
-------------------------------

The built-in webserver can be used to quickly ensure that everything is working
as expected

.. code-block:: bash

    $ essarch devserver

The web service should now be accessible in your web browser at
http://localhost:8000


.. warning::

   The built-in webserver is not recommended for production usage, instead a
   dedicated web server such as Nginx or Apache should be setup.
