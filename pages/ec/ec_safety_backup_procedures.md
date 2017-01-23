---
title: Safety backup procedures
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Safety backup procedures"
sidebar: ec_sidebar
permalink: ec_safety_backup_procedures.html
folder: ec
---

## Important files to backup

Important data in ESSArch to backup is the configuration, log files and database. All areas which are mounted from external file servers should be backed up.

Everything in the file area /ESSArch should be backed up before and after configuration changes or changes in ESSArch system installation, for example when upgrading and software patches.

Areas that need to be backed up to an external "backup system" daily is the following:

- /ESSArch/backup
- /ESSArch/config
- /ESSArch/log
- /ESSArch/data

[<img align="right" src="images/n.png">][ec_logfiles]

{% include links.html %}
