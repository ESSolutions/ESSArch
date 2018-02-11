---
title: Running the EPP server
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Running the EPP server"
sidebar: epp_sidebar_2_8
permalink: epp_running_2_8.html
folder: epp_2_8
---

## Running the EPP server

### Start EPP server

Note that a startup or shutdown of EPP should always be controlled.

    Please run the following command as user root to start EPP.
    # systemctl start celerydepp
    # systemctl start celerybeatepp
    # systemctl start essarch
    # systemctl start esshttpd

### Stop EPP server

    Please run the following command as user root to stop EPP.
    # systemctl stop esshttpd
    # systemctl stop essarch
    # systemctl stop celerydepp
    # systemctl stop celerybeatepp

### Access EPP web user interface

Start your preferable web browser and connect to EPP Server name or IP address.

URL: https://xxxxxxxx

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions**  |
| --- | --- | --- |
| user | user | prepare, create, submit |
| admin | admin | admin |
| sysadmin | sysadmin | sysadmin |

[<img align="right" src="images/n.png">](epp_safety_backup_procedures_2_8.html)
{% include links.html %}
