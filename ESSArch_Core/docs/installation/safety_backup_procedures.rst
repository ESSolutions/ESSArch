.. _core-safety-backup-procedures:

************************
Safety backup procedures
************************


Important files to backup
=========================

Important data in ESSArch to backup is the configuration, log files and
database. All areas which are mounted from external file servers should be
backed up.

Everything in the file area /ESSArch should be backed up before and after
configuration changes or changes in ESSArch system installation, for example
when upgrading ESSArch or its dependencies.

Areas that need to be backed up to an external “backup system” daily is the
following:

   * /ESSArch/backup
   * /ESSArch/config
   * /ESSArch/log
   * /ESSArch/data
