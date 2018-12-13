.. _profiles:

**************
 Profiles
**************

Validation
==========

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

ChecksumValidator
^^^^^^^^^^^^^^^^^

.. autoclass:: ESSArch_Core.fixity.validation.backends.checksum.ChecksumValidator
   :members:

StructureValidator
^^^^^^^^^^^^^^^^^^

.. autoclass:: ESSArch_Core.fixity.validation.backends.structure.StructureValidator
   :members:

MediaconchValidator
^^^^^^^^^^^^^^^^^^

.. autoclass:: ESSArch_Core.fixity.validation.backends.mediaconch.MediaconchValidator
   :members:


VeraPDFValidator
^^^^^^^^^^^^^^^^^^

.. autoclass:: ESSArch_Core.fixity.validation.backends.verapdf.VeraPDFValidator
   :members:


Transformation
==============

Specification
-------------

``name`` specifies which transformer in :ref:`essarch_transformers` that should
be used
