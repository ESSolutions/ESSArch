.. _format-identifier:

================
 Format Identifier
================


.. autoclass:: ESSArch_Core.fixity.format.FormatIdentifier
   :members:

FormatIdentifier is used to identify the format of files during validation, XML
generation and viewing files in the browser.

.. _mimetypes:

MIME types
---------

The file at :ref:`path_mimetypes_definitionfile` is used to identify the MIME
type of the file.  If the file extension is missing from the MIME types file it
will be set to ``application/octet-stream`` if ``allow_unknown_file_types`` is
set to ``True``. If ``allow_unknown_file_types`` is set to ``False`` an
exception will be raised.

.. _fido:

Fido
---------

The fido library is used to get the format name, version and registry key of
the file.
