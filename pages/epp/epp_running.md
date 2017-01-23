---
title: Running the EPP server
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Running the EPP server"
sidebar: epp_sidebar
permalink: epp_running.html
folder: epp
---

## Running the EPP server

### Start EPP server

Note that a startup or shutdown of EPP should always be controlled.

    Please run the following command as user root to start EPP.
    # service celeryd start
    # service celerybeat start
    # service essarch start
    # service esshttpd start

### Stop EPP server

    Please run the following command as user root to stop EPP.
    # service esshttpd stop
    # service essarch stop
    # service celeryd stop
    # service celerybeat stop

### Access EPP web user interface

Start your preferable web browser and connect to EPP Server name or IP address.

URL: https://xxxxxxxx

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions**  |
| --- | --- | --- |
| user | user | prepare, create, submit |
| admin | admin | admin |
| sysadmin | sysadmin | sysadmin |

[<img align="right" src="images/n.png">](epp_safety_backup_procedures.html)
{% include links.html %}
