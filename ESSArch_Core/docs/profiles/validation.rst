.. _validation_profile:

*******************
 Validation Profile
*******************

Specification
-------------

Each key (except those beginning with ``_``) in the specification specifies a
validator that should be used.

.. note::

    The ``_required`` key can be used to specify a list of validators that must
    pass when executed.

Each validator key is a list of configurations of the validator that should be
applied on different sets of files.

* ``exclude`` - A list of relative paths that should be excluded from the validation
* ``include`` - A list of relative paths that should be included in the validation
* ``context`` - Specifies how and/or where is the correct value stored
* ``options`` - A dict with validator-specific options

.. note::

    XML-variables can be used with the ``{VARIABLE}``-syntax in the
    configuration values. See :ref:`xml-variables` for more information.



Built-in validators
-------------------
ESSArch has a range of built-in :ref:`preservation-tools-validators`

* :ref:`checksum_validator`

* :ref:`csv_validator`

* :ref:`encryption_validator`

* :ref:`filename_validator`

* :ref:`fixed_width_validator`

* :ref:`file_format_validator`

* :ref:`folder_structure_validator`

* :ref:`mediaconch_validator`

* :ref:`repeated_extension_validator`

* :ref:`verapdf_validator`

* :ref:`warc_validator`

* :ref:`xml_validator`
