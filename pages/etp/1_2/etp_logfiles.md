---
title: Logfiles
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Logfile"
sidebar: etp_sidebar_1_2
permalink: etp_logfiles_1_2.html
folder: etp_1_2
---

## Events and log information

Different types of events are logged both in physical files and tables in
ESSArch database. Log entries are tagged with the log level - Debug, Critical,
Error, Warning, Info. List of log files:

- /ESSArch/log
- /ESSArch/log/celery_workeretp.log
- /ESSArch/log/celery_workeretpfileoperation.log
- /ESSArch/log/celery_workeretpvalidation.log
- /ESSArch/log/httpd_access_etp.log
- /ESSArch/log/httpd_error_etp.log
- /ESSArch/log/httpd_ssl_request_etp.log

{% include links.html %}
