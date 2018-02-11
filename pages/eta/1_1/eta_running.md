---
title: Running the ETA server
tags: [getting_started, troubleshooting]
keywords:
last_updated: Jan 15, 2017
summary: "Running the ETA server"
sidebar: eta_sidebar_1_1
permalink: eta_running_1_1.html
folder: eta_1_1
---

## Running the ETA server

### Start ETA server

Note that a startup or shutdown of ETA should always be controlled.

    Please run the following command as user root to start ETA.
    # service celerydeta start
    # service esshttpd start

### Stop ETA server

    Please run the following command as user root to stop ETA.
    # service esshttpd stop
    # service celerydeta stop

### Access ETA web user interface

Start your preferable web browser and connect to ETA Server name or IP address.

URL: https://xxxxxxxx

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions**  |
| --- | --- | --- |
| user | user | prepare, create, submit |
| admin | admin | admin |
| sysadmin | sysadmin | sysadmin |

[<img align="right" src="images/n.png">](eta_safety_backup_procedures_1_1.html)
{% include links.html %}
