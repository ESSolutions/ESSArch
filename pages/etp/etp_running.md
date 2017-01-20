---
title: Running the ETP server
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Running the ETP server"
sidebar: etp_sidebar
permalink: etp_running.html
folder: etp
---

## Running the ETP server

### Start ETP server

Note that a startup or shutdown of ETP should always be controlled.

    Please run the following command as user root to start ETP.
    # service celerydetp start
    # service esshttpd start

### Stop ETP server

    Please run the following command as user root to stop ETP.
    # service esshttpd stop
    # service celerydetp stop

### Access ETP web user interface

Start your preferable web browser and connect to ETP Server name or IP address.

URL: https://xxxxxxxx

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions**  |
| --- | --- | --- |
| user | user | prepare, create, submit |
| admin | admin | admin |
| sysadmin | sysadmin | sysadmin |

[<img align="right" src="images/n.png">](etp_safety_backup_procedures.html)
{% include links.html %}
