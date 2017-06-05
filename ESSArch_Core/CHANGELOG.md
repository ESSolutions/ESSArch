# [1.1.0](https://github.com/ESSolutions/ESSArch_Core/releases/tag/1.1.0)


## Workflow Engine
### Features and improvements

* Removed `celery_id` field from `ProcessTask`. Instead we set
  the id of the celery id to the same as the id of the task
* Removed " undo" prefix from undo-tasks
* The status and progress of steps are now cached using Redis
* Added `eager` field to steps and tasks determine if tasks should be executed
  locally or sent to queue
* Removed `attempt` field from `ProcessTask`. Instead we use
  `undone` and `retried` fields that are foreign keys to the tasks that are
  undone/retried
* Removed `id` field from `EventType`. `eventType` is now used as the
  primary key
* Added a `chunk` method to `ProcessStep` which enables us to run multiple
  tasks (of the same type) in a single celery message
* Tasks now always expects id of objects instead of the objects themselves as paramaters
* Tasks now accepts positional arguments using the `args` list field
* If the destination of `CopyFile` is a directory then the file will be put in that directory
* Added `ConvertFile` task
* `CreateTar` and `CreateZIP` has been imported from ETP and have gotten support for compression
* When copying a local file with `CopyFile`, the destination directory will be created if needed
* Multipart-Encoded files are now used for remote file transfers
* A final request with the path and MD5 checksum is sent when all chunks have
  been uploaded to the same URL as the file uploads but with `_complete` added
  to the end
* If the request in `DownloadFile` fails, an exception is raised
* Certificates are no longer verified in `DownloadFile`
* Serializers and views for steps and tasks has been imported from ETP
* `params` and `result_params` can no longer be `None`
* `result_params` are now `{}` by default
* `result_params` are now merged into `params` in task serializer
* Tasks and steps can now be filtered on the `hidden` field



### Bug Fixes
* Previous results are no longer fetched before the previous task is done
* Running an empty step no longer crashes and returns an empty list instead
* Events created in a task are now created before the next task starts
* `HTTP_CONTENT_RANGE` is now correctly set when transferring files


## XML Generator

### Features and improvements
* `ObjectIdentifierValue` instead of `ìd` is now used for `_OBJID`
* External XML files are now supported

    Using the `-external` key in the specification, one can specify that the
    generated xml should be split up into multiple files. The key will point
    to a dict containing 4 keys:

    * `-dir`: The parent directory to all the directories that will get an
      external file
    * `-file`: The name of all external files
    * `-pointer`: The specification for the pointers to the external files
    * `-specification`: The specification of all external files

* `einfo` has been replaced by `traceback` and `exception` in `ProcessTask` to
  support exceptions that cannot be pickled
* Added a view for the current user
* Root directory, file format name, file format version and file format
  registry key are now included in the result of `ParseFile`
* An element can now be flagged as required with the `-req` flag
* An element can now be flagged with `-hideEmptyContent` which will hide the
  element if it doesn't have any content

### Bug Fixes
* XML Generator can now parse files with names containing non-ascii characters

## Misc
* A `UserProfile` model has been added which has a one-to-one relation with the `User` model
* Added permission `ip.can_upload`
* Added permission `profiles.can_create_new_sa_generation`
* Added `in_directory` to `util` which can be used to check if one path is a sub path of another path
* When creating a new profile generation, any connection to a IP is no longer changed
* URL fields in profiles are now validated on clean
* Profiles are no validated when creating new generations
* All fields in the `InformationPackage`-model are now in snake\_case

## Requirement changes
### Updates
* Updated `django-filter` from `0.15.2` to `1.0.3`
* Updated `djangorestframework` from `3.4.6` to `3.6.3`
* Updated `opf-fido` from `1.3.4` to `1.3.5`
* Updated `scandir` from `1.3` to `1.4`

### Additions
* Added `django-mptt 0.8.7`
* Added `drf-extensions 0.3.1`
* Added `drf-proxy-pagination 0.1.1`
* Added `httpretty 0.8.14`
* Added `mock 2.0.0`
* Added `mysqlclient 1.3.10`
* Added `natsort 5.0.2`
* Added `requests_toolbelt 0.7.0`
