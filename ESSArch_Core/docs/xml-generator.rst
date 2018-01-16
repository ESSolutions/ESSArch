.. _xml-generator:

================
 XML Generator
================

.. seealso::

    :ref:`profiles`

Specification syntax
--------------------

.. _xml-variables:

XML Variables
--------------------

XML variables are what allows us to reuse the same profile for multiple IPs
with different values.

In the specification for a XML file we can write the following to define an
element with its text set to a variable

.. code-block:: json

    {
        "-name": "myelement",
        "#content": [{"var": "myvar"}]
    }

If we create this with ``myvar = "hello world"`` we get the following XML

.. code-block:: xml

    <myelement>hello world</myelement>

We could also add a static prefix and/or suffix

.. code-block:: json

    {
        "-name": "myelement",
        "#content": [{"text": "hello "}, {"var": "myvar"}, {"text": ", how are you?"}]
    }

Used with ``myvar = "world"`` we get

.. code-block:: xml

    <myelement>hello world, how are you?</myelement>

.. _reserved-xml-variables:

Reserved XML Variables
^^^^^^^^^^^^^^^^^^^^^^

This is a list of reserved variables that can be used in profiles to get more
dynamic, automatically populated data.

====================================== =====
``_UUID``                              Generates a new UUID
``_OBJID``                             ID of the IP
``_OBJUUID``                           UUID of the IP
``_OBJLABEL``                          Label of the IP
``_OBJPATH``                           Path of the IP
``_STARTDATE``                         Start date of the IP
``_ENDDATE``                           End date of the IP
``_NOW``                               Time at generation of element
``_USER``                              Logged in user
``_XML_FILENAME``                      Name of XML file being generated
``_EXT``                               The directory name for the current external XML file
``_EXT_HREF``                          The directory path and name for the current external XML file
``_IP_CREATEDATE``                     Timestamp of when the tar/zip-file was generated
``_IP_CONTAINER_FORMAT``               The container format of the IP, e.g. tar or zip
``_SA_ID``                             The id of the Submission Agreement
``_SA_NAME``                           The name of the Submission Agreement
``_IP_ARCHIVIST_ORGANIZATION``         The archivist organization of the Information Package
``_INFORMATIONCLASS``                  The information class of the Information Package
``_POLICYUUID``                        The policy uuid of the Information Package
``_POLICYID``                          The policy id of the Information Package
``_POLICYNAME``                        The policy name of the Information Package
``_PROFILE_TRANSFER_PROJECT_ID``       transfer project profile id
``_PROFILE_SUBMIT_DESCRIPTION_ID``     submit description profile id
``_PROFILE_SIP_ID``                    sip profile id
``_PROFILE_AIP_ID``                    aip profile id
``_PROFILE_DIP_ID``                    dip profile id
``_PROFILE_CONTENT_TYPE_ID``           content type profile id
``_PROFILE_AUTHORITY_INFORMATION_ID``  authority information profile id
``_PROFILE_ARCHIVAL_DESCRIPTION_ID``   archival description profile id
``_PROFILE_PRESERVATION_METADATA_ID``  preservation metadata profile id
``_PROFILE_DATA_SELECTION_ID``         data selection profile id
``_PROFILE_IMPORT_ID``                 import profile id
``_PROFILE_WORKFLOW_ID``               workflow profile id
====================================== =====

In addition to the list above, all parameters can also be accessed with the
``_PARAMETER_{ENTITY}`` syntax where ``{ENTITY}`` is the name of the parameter.
