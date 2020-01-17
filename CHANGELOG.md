# [3.1.1](https://github.com/ESSolutions/ESSArch/releases/tag/3.1.1)

## Fixed

- Rules for moving structure unit instances (#850, #852, #863)
- Assigned roles section on user admin page (#868)

# [3.1.0](https://github.com/ESSolutions/ESSArch/releases/tag/3.1.0)

## Added

- XML comparison of METS and PREMIS in IP representations (#593)
- saml2 route to API when ENABLE_ADFS_LOGIN is enabled (#605)
- Favicon (#604)
- XML schema downloading for AIPs in manual workflow (#645)
- Event file creation to AIPs in manual workflow (#674)
- XML schema validator to CLI (#643)
- Mediaconch validator to CLI (#787)
- Ability to download DIPs and orders (#661)
- METS data from SIP is now parsed and stored in AIP profile during ingest (#673)
- More advanced DIP creation similar to SIP creation (#688)
- Ability to store data for IP and SA relation (#697)
- Receipt path configuration (#710)
- Protection against problematic characters in IP identifiers (#722)
- New storage maintenance page (#663)
- Ability to specify custom task references in order to use results as parameters to other tasks in the same step (#734)
- Makulerat and Recno to XML receipts (#790, #797)
- Ability to attach xml receipt to email receipt (#794)
- EARK 2.0.x profiles (#830)

## Changed

- Build dev version of frontend in docker (#682)
- Only show relevant filters for IPs and events (#582)

## Fixed

- Docs generation and removed redundant step in docker build (#564)
- XML validation against schemas with https imports (#642)
- XML validation against schemas specified in `schemaLocation` attribute (#651)
- Default ELASTICSEARCH_CONNECTIONS (#669)
- Copying of empty subdirectories (#675)
- Usage of checksum algorithm (#708)
- mets@TYPE options in SE profiles (#716)
- IDs in XML receipts (#790)

# [3.0.1](https://github.com/ESSolutions/ESSArch/releases/tag/3.0.1)

## Changed

- Use debug mode in docker as default (#569)

## Fixed

- Fixed bug when trying to edit archive with unpublished structure (#591)

# [3.0.0](https://github.com/ESSolutions/ESSArch/releases/tag/3.0.0)

## Introduction

The 3.0.0 release of ESSArch includes lots of new functionality as well as improvements in UI and
backend stability.
Though the biggest change is that the new ESSArch contains all the functionality previously
found in ESSArch Core and our three products: [ESSArch Tools For Producer](https://github.com/ESSolutions/ESSArch_Tools_Producer), [ESSArch Tools For Archive](https://github.com/ESSolutions/ESSArch_Tools_Archive) and [ESSArch Preservation Platform](https://github.com/ESSolutions/ESSArch_EPP).

## Important notes

- Merged ESSArch core, ESSArch Tools For Producer, ESSArch Tools For Archive and ESSArch
  Preservation Platform into one single ESSArch application
- The usual ESSArch workflows are still possible and relevant in the new version. The only difference is that now it is done through
  configurations rather than installing several applications which gives more possibilities since every function of ESSArch
  can be made available for any user.

## Updates or refinement of existing OAIS functional entities

- Pre-Ingest functionality to prepare IPs, collect content, create SIPs and submit SIPs to archival institutions
- Ingest functionality to receive and ingest SIPs, perform SIP2AIP, store AIPs in different archival storage's and provide search and access functionality
- Access functionality to search, retrieve (e.g DIPs) and view archived objects
- Data Management functionality to support generations of IPs, versioning and relation management between different sets of metadata
- Administration functionality to manage policies, profiles, storage methods, Submission Agreements and media information
- Preservation planning functionality to maintain integrity, fixity, and consistency of archived objects beside operations of the archive like disposal, removal and migration
- Workflows (task/steps) and event management will, as previous, be represented and configurable in ESSArch,
- Different converters, validators and transformers will, as previous, be possible to use in automatic workflows

## Features and improvements

- Functionality for archival descriptions, authority records, accession management and physical location management. This will cover both digital and analogue archival management.
- Support for PREFORMA file format validations Vera PDF and Mediaconch
- Duplex integration with ERMS system Public 360
- Indexing of ERMS deliveries (SIPs) in order to support search functionality of received information objects
- Extended converting support i.e converting of Image Magick formats (bmp/cals/x-cals/jpeg/png) and OpenSSL certificates and sie4 (Swedish exchange format for financial information) to csv.
- Support for physical map structure transformation
- Added default docker image for development and testing
- Extended support for Submission agreement and profile management

### User interface

- Improvements in UI and usability
- Reorganized menus to make using the entire ESSArch platform or just small parts easier
- Introduce use of modern tools such as Webpack 4, Babel and Typescript in frontend development

### Server

- Improved overall product stability
- Use python minimum 3.7.0

## Database requirements

- Now supports PostgreSQL 9.4 and higher
- Now supports MySQL 5.6 and higher
- Now supports SQLite 3.8.3 and higher
- Support for Microsoft SQL Server 2008+ has been added using [django-mssql-backend](https://pypi.org/project/django-mssql-backend/)

## Updated services

- Elasticsearch - version 6.5.4

## Last notes

All further development of the ESSArch platform will be done in this "merged" version of ESSArch.

# [1.1.0](https://github.com/ESSolutions/ESSArch_Core/releases/tag/1.1.0)

## Important notes

### [Redis](https://redis.io) is now a OS package prerequisite

- Redis is used for caching different parts of the system for improved performance and is now required for ESSArch to work properly.
- See [ESSArch Core installation documentation](https://essolutions.github.io/ESSArch_Core/ec_prerequisites.html#redis-new-in-110) for more information

## Workflow Engine

### Features and improvements

- Removed `celery_id` field from `ProcessTask`. Instead we set
  the id of the celery id to the same as the id of the task
- Removed " undo" prefix from undo-tasks
- The status and progress of steps are now cached using Redis
- Added `eager` field to steps and tasks determine if tasks should be executed
  locally or sent to queue
- Removed `attempt` field from `ProcessTask`. Instead we use
  `undone` and `retried` fields that are foreign keys to the tasks that are
  undone/retried
- Removed `id` field from `EventType`. `eventType` is now used as the
  primary key
- Added a `chunk` method to `ProcessStep` which enables us to run multiple
  tasks (of the same type) in a single celery message
- Tasks now always expects id of objects instead of the objects themselves as paramaters
- Tasks now accepts positional arguments using the `args` list field
- If the destination of `CopyFile` is a directory then the file will be put in that directory
- Added `ConvertFile` task
- `CreateTar` and `CreateZIP` has been imported from ETP and have gotten support for compression
- When copying a local file with `CopyFile`, the destination directory will be created if needed
- Multipart-Encoded files are now used for remote file transfers
- A final request with the path and MD5 checksum is sent when all chunks have
  been uploaded to the same URL as the file uploads but with `_complete` added
  to the end
- If the request in `DownloadFile` fails, an exception is raised
- Certificates are no longer verified in `DownloadFile`
- Serializers and views for steps and tasks has been imported from ETP
- `params` and `result_params` can no longer be `None`
- `result_params` are now `{}` by default
- `result_params` are now merged into `params` in task serializer
- Tasks and steps can now be filtered on the `hidden` field

### Bug Fixes

- Previous results are no longer fetched before the previous task is done
- Running an empty step no longer crashes and returns an empty list instead
- Events created in a task are now created before the next task starts
- `HTTP_CONTENT_RANGE` is now correctly set when transferring files

## XML Generator

### Features and improvements

- `ObjectIdentifierValue` instead of `ìd` is now used for `_OBJID`
- External XML files are now supported

  Using the `-external` key in the specification, one can specify that the
  generated xml should be split up into multiple files. The key will point
  to a dict containing 4 keys:

  - `-dir`: The parent directory to all the directories that will get an
    external file
  - `-file`: The name of all external files
  - `-pointer`: The specification for the pointers to the external files
  - `-specification`: The specification of all external files

- `einfo` has been replaced by `traceback` and `exception` in `ProcessTask` to
  support exceptions that cannot be pickled
- Added a view for the current user
- Root directory, file format name, file format version and file format
  registry key are now included in the result of `ParseFile`
- An element can now be flagged as required with the `-req` flag
- An element can now be flagged with `-hideEmptyContent` which will hide the
  element if it doesn't have any content
- If `allow_unknown_file_types` is `True` then mimetypes of unknown file types will be set to `application/octet-stream`

### Bug Fixes

- XML Generator can now parse files with names containing non-ascii characters

## Misc

- A `UserProfile` model has been added which has a one-to-one relation with the `User` model
- Added permission `ip.can_upload`
- Added permission `profiles.can_create_new_sa_generation`
- Added `in_directory` to `util` which can be used to check if one path is a sub path of another path
- When creating a new profile generation, any connection to a IP is no longer changed
- URL fields in profiles are now validated on clean
- Profiles are no validated when creating new generations
- All fields in the `InformationPackage`-model are now in snake_case
- Locking a profile with fields in template missing in `specification_data` will now copy the default value of those fields into `specification_data`

## Requirement changes

### Updates

- Updated `django-filter` from `0.15.2` to `1.0.3`
- Updated `djangorestframework` from `3.4.6` to `3.6.3`
- Updated `opf-fido` from `1.3.4` to `1.3.5`
- Updated `scandir` from `1.3` to `1.4`

### Additions

- Added `django-mptt 0.8.7`
- Added `drf-extensions 0.3.1`
- Added `drf-proxy-pagination 0.1.1`
- Added `httpretty 0.8.14`
- Added `mock 2.0.0`
- Added `mysqlclient 1.3.10`
- Added `natsort 5.0.2`
- Added `requests_toolbelt 0.7.0`
