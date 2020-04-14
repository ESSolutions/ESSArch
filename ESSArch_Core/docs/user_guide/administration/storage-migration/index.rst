.. _storage-migration:

******************
Storage migration
******************

Storage migration basically means moving data from one storage target to another.

Select storage mediums
======================
When migrating information packages we start by selecting storage mediums that contains the
information packages.
When a storage medium is visible in the storage medium table it means that it has information packages
that has a storage target with status "Migrate" and the storage method has a storage target with status
"Enabled" that does not yet have given.

The storage medium list has two filtering options, storage policy and medium ID (single or range).
Mediums can be filtered by storage policy which is initially set to the first storage policy.
The storage policy filter is required and will always have a value to ble able to populate the storage medium
list.
The medium ID filter has two different variations. The first option is to search and select on single
storage medium which filters out selected medium. The second is for filtering out a range of mediums.
The medium ID range filter can be activated by checking the checkbox labeled **Enter medium ID range**.
This checkbox also disables the single medium ID option and clears it's value.
The range filter allows a user to select the first and last medium ID by searching and selecting
medium IDs.
When unchecking the checkbox the range filter is disabled and its values are cleared in favor of
single medium ID filtering.

Select Information packages
===========================

Multiple storage mediums can be selected by clicking the corresponding rows in the storage medium table.
When at least one storage medium is selected the information package list is visible which is where
we select which information packages we want to migrate.
The information packe list is filtered by selected mediums in the storage medium list, which means
that if multiple mediums are selected, IP's stored on one of the selected mediums will be visible.

The IP list works in the same way as other IP list views in ESSArch and we can view the job and event list
as well as the filebrowser and the main "Migrate" tab which is where we proceed with the migration process
after selecting IPs for migration (choose multiple by holding the alt/shift key and clicking as usual).
When IPs are selected click the **Start migration** button.

Storage migration options
=========================

In the storage migration modal window we get a list of selected information packages along with options
for the migration job.

**Temporary path** is where the content we are migrating will be stored during the data move, it is
prepopulated with configured temp path.

**Purpose** is a text field that will be used as comment for the storage migration event.

**Migrate to all storage targets** is checked by default which means that the migration job will migrate
to all storage methods for each selected IP. Unchecking this option enables a select box which allows
multiple choices and search where storage methods can be manually selected for migration.

Preview storage migration
=========================

When all options for storage migrations looks OK we can preview the migration to see information packages
that will be migrated along with storage targets for each IP. Clicking an IP row will expand it and show
which storage targets it will be migrated to.

Start storage migration
=======================

It the preview looks good, then we are ready to start the migration job by first closing the preview window
then clicking the **Start migration** button.

All migration jobs can be found under the **Migration tasks** tab. Click a migration job row to see the
task information modal.
