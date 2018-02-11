---
title: Running the ETP server
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Running the ETP server"
sidebar: etp_sidebar_1_2
permalink: etp_running_1_2.html
folder: etp_1_2
---

## Running the ETP server

### Start ETP server

Note that a startup or shutdown of ETP should always be controlled.

    Please run the following command as user root to start ETP.
    # systemctl start celerydetp
    # systemctl start daphneetp
    # systemctl start wsworkeretp
    # systemctl start esshttpd

### Stop ETP server

    Please run the following command as user root to stop ETP.
    # systemctl stop esshttpd
    # systemctl stop celerydetp
    # systemctl stop daphneetp
    # systemctl stop wsworkeretp

### Access ETP web user interface

Start your preferable web browser and connect to ETP Server name or IP address.

URL: https://xxxxxxxx

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions**  |
| --- | --- | --- |
| user | user | prepare, create, submit |
| admin | admin | admin |
| sysadmin | sysadmin | sysadmin |

[<img align="right" src="images/n.png">](etp_safety_backup_procedures_1_2.html)
{% include links.html %}
