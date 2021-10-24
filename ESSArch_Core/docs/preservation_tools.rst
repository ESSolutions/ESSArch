.. _preservation_tools:

==================
Preservation tools
==================

.. _preservation-tools-converters:

Converters
----------

.. _imagemagick:

Image(Magick)
=============

.. autoclass:: ESSArch_Core.fixity.conversion.backends.image.ImageConverter
   :members:

ESSArchs image converter uses ImageMagick to convert images to and from a variety of `formats <https://imagemagick.org/script/formats.php>`_ (over 200) including PNG, JPEG, GIF, WebP, HEIC, SVG, PDF, DPX, EXR and TIFF.

.. _openssl:

Openssl
=======

.. autoclass:: ESSArch_Core.fixity.conversion.backends.openssl.OpenSSLConverter
   :members:


SIARD -> SQLITE
===============
.. autoclass:: ESSArch_Core.fixity.conversion.backends.siard.SiardConverter
   :members:


SIE -> CSV
==========
.. autoclass:: ESSArch_Core.fixity.conversion.backends.sie.SIEConverter
   :members:



Characterisation tools
----------------------

Format Identifier
=================

.. autoclass:: ESSArch_Core.fixity.format.FormatIdentifier
   :members:

FormatIdentifier is used to identify the format of files during validation, XML
generation and viewing files in the browser.


Normalizers and transformers
----------------------------


Content Folder
==============
.. autoclass:: ESSArch_Core.fixity.transformation.backends.content.ContentTransformer
   :members:

Filename Transformer
====================

.. autoclass:: ESSArch_Core.fixity.transformation.backends.filename.FilenameTransformer
   :members:

Repeated Extensions
===================

.. autoclass:: ESSArch_Core.fixity.transformation.backends.repeated_extension.RepeatedExtensionTransformer
   :members:

.. _preservation-tools-validators:

Validators
----------

.. _checksum_validator:

Checksum
========

.. autoclass:: ESSArch_Core.fixity.validation.backends.checksum.ChecksumValidator
   :members:


.. _csv_validator:

CSV
===

.. autoclass:: ESSArch_Core.fixity.validation.backends.csv.CSVValidator
   :members:

.. _encryption_validator:

Encryption
==========
.. autoclass:: ESSArch_Core.fixity.validation.backends.encryption.FileEncryptionValidator
   :members:


.. _filename_validator:

Filename
========
.. autoclass:: ESSArch_Core.fixity.validation.backends.filename.FilenameValidator
   :members:

.. _fixed_width_validator:

Fixed Width
===========
.. autoclass:: ESSArch_Core.fixity.validation.backends.fixed_width.FixedWidthValidator
   :members:

.. _file_format_validator:

File Format
===========
ESSArch uses FIDO for file-format identification which in turn uses the
UK National Archives (TNA) PRONOM File Format and Container descriptions.
PRONOM is available from `http://www.nationalarchives.gov.uk/pronom/ <http://www.nationalarchives.gov.uk/pronom/>`_

.. autoclass:: ESSArch_Core.fixity.validation.backends.format.FormatValidator
   :members:


.. _folder_structure_validator:

Folder Structure
================
.. autoclass:: ESSArch_Core.fixity.validation.backends.structure.StructureValidator
   :members:


.. _mediaconch_validator:

MediaConch
==========
MediaConch is an extensible, open source software project consisting of an
implementation checker, policy checker,reporter, and fixer that targets
preservation-level audiovisual files (specifically Matroska, Linear Pulse Code Modulation (LPCM) and FF Video Codec 1 (FFV1))
for use in memory institutions, providing detailed conformance
checking.

.. autoclass:: ESSArch_Core.fixity.validation.backends.mediaconch.MediaconchValidator
   :members:

.. _repeated_extension_validator:

Repeated Extensions
===================
.. autoclass:: ESSArch_Core.fixity.validation.backends.repeated_extension.RepeatedExtensionValidator
   :members:

.. _verapdf_validator:

VeraPDF
=======
VeraPDF is a purpose-built, open source file-format validator covering all
PDF/A parts and conformance levels.

.. autoclass:: ESSArch_Core.fixity.validation.backends.verapdf.VeraPDFValidator
   :members:

.. _warc_validator:

Warc
====

.. autoclass:: ESSArch_Core.fixity.validation.backends.warc.WarcValidator
   :members:

.. _xml_validator:

XML
===

.. _diffcheck_xml_validator:

Diffcheck
_________

.. autoclass:: ESSArch_Core.fixity.validation.backends.xml.DiffCheckValidator
   :members:

Comparison Validator
____________________

.. autoclass:: ESSArch_Core.fixity.validation.backends.xml.XMLComparisonValidator
   :members:

Schema Validator
________________

.. autoclass:: ESSArch_Core.fixity.validation.backends.xml.XMLSchemaValidator
   :members:

Syntax Validator
________________

.. autoclass:: ESSArch_Core.fixity.validation.backends.xml.XMLSyntaxValidator
   :members:

Schematron Validator
____________________

.. autoclass:: ESSArch_Core.fixity.validation.backends.xml.XMLSchematronValidator
   :members:

ISO Schematron Validator
________________________

.. autoclass:: ESSArch_Core.fixity.validation.backends.xml.XMLISOSchematronValidator
   :members:



.. _mimetypes:

MIME types
==========

The file at :ref:`path_mimetypes_definitionfile` is used to identify the MIME
type of the file.  If the file extension is missing from the MIME types file it
will be set to ``application/octet-stream`` if ``allow_unknown_file_types`` is
set to ``True``. If ``allow_unknown_file_types`` is set to ``False`` an
exception will be raised.

