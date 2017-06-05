---
title: Upgrade ESSArch Tools Archive
permalink: eta_upgrade.html
keywords: ESSArch Tools Archive
sidebar: eta_sidebar
folder: eta
---

## Stop services
* esshttpd
* celeryd
* celerydeta
* rabbitmq-server
* redis

## Verify that a backup of the database exists at `/ESSArch/backup`

## Move old installation

    cd /ESSArch
    mkdir old
    mv config install install*.log pd old/

## Install new ESSArch Tools Archive

    # su - arch
    [arch@server ~]$ tar xvf ESSArch_TA_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_TA_installer-x.x.x
    [arch@server ~]$ ./install

### Collect static files to be served by apache httpd

    [arch@server ~]$ python $ETA/manage.py collectstatic

### Upgrade database schema (ensure that the storage engine is correct)

    [arch@server ~]$ python $ETA/manage.py migrate

### Add default configuration data to database

    [arch@server ~]$ python $ETA/install/install_default_config_eta.py

## Compare and restore configuration files at `/ESSArch/config` from `old` directory
    # diff -qr /ESSArch/config old

## Start services

* esshttpd
* celeryd
* celerydeta
* rabbitmq-server
* redis
