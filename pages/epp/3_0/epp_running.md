---
title: Running the EPP server
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Running the EPP server"
sidebar: epp_sidebar_3_0
permalink: epp_running_3_0.html
folder: epp_3_0
---

## Running the EPP server

### Start EPP server

Note that a startup or shutdown of EPP should always be controlled.

    Please run the following command as user root to start EPP.
    # systemctl start celerydepp
    # systemctl start celerybeatepp
    # systemctl start daphneepp
    # systemctl start wsworkerepp
    # systemctl start esshttpd

### Stop EPP server

    Please run the following command as user root to stop EPP.
    # systemctl stop esshttpd
    # systemctl stop celerydepp
    # systemctl stop celerybeatepp
    # systemctl stop daphneepp
    # systemctl stop wsworkerepp

### Access EPP web user interface

Start your preferable web browser and connect to EPP Server name or IP address.

URL: https://xxxxxxxx

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions**  |
| --- | --- | --- |
| user | user | prepare, create, submit |
| admin | admin | admin |
| sysadmin | sysadmin | sysadmin |

[<img align="right" src="images/n.png">](epp_safety_backup_procedures_3_0.html)
{% include links.html %}
