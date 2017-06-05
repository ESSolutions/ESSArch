---
title: Upgrade ESSArch Preservation Platform
permalink: epp_upgrade.html
keywords: ESSArch Preservation Platform
sidebar: epp_sidebar
folder: epp
---

## Stop services
* esshttpd
* celeryd
* celerybeat
* rabbitmq-server

## Verify that a backup of the database exists at `/ESSArch/backup`

## Move old installation

    cd /ESSArch
    mkdir old
    mv config install install*.log pd old/

## Install new ESSArch Preservation Platform

    # su - arch
    [arch@server ~]$ tar xvf ESSArch_EPP_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_EPP_installer-x.x.x
    [arch@server ~]$ ./install
    [arch@server ~]$ export EPP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_EPP
    [arch@server ~]$ export PYTHONPATH=$EPP:$EPP/workers:$EC_PYTHONPATH


### Collect static files to be served by apache httpd

    [arch@server ~]$ python $EPP/manage.py collectstatic

### Upgrade database schema (ensure that the storage engine is correct)

    [arch@server ~]$ python $EPP/manage.py migrate

### Add default configuration data to database
*Note: Before running the script, compare it with the data currently in the database and see if running it is necessary*

    [arch@server ~]$ python $EPP/extra/install_config.py

## Compare and restore configuration files at `/ESSArch/config` from `old` directory
    # diff -qr /ESSArch/config old

## Start services

* esshttpd
* celeryd
* celerybeat
* rabbitmq-server
