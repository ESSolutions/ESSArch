---
title: Upgrade ESSArch Tools Producer
permalink: etp_upgrade.html
keywords: ESSArch Tools Producer
sidebar: etp_sidebar
folder: etp
---

## Stop services
* esshttpd
* celeryd
* celerydetp
* rabbitmq-server
* redis

## Verify that a backup of the database exists at `/ESSArch/backup`

## Move old installation

    # cd /ESSArch
    # mkdir old
    # mv config install install*.log pd old/

##  Install new ESSArch Tools Producer

    # su - arch
    [arch@server ~]$ tar xvf ESSArch_TP_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_TP_installer-x.x.x
    [arch@server ~]$ ./install
    [arch@server ~]$ export ETP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_TP
    [arch@server ~]$ export PYTHONPATH=$ETP:$EC_PYTHONPATH

### Collect static files to be served by apache httpd

    [arch@server ~]$ python $ETP/manage.py collectstatic

### Upgrade database schema (ensure that the storage engine is correct)

    [arch@server ~]$ python $ETP/manage.py migrate

### Add default configuration data to database

    [arch@server ~]$ python $ETP/install/install_default_config_etp.py

## Compare and restore configuration files at `/ESSArch/config` from `old` directory
    # diff -qr /ESSArch/config old

## Start services

* esshttpd
* celeryd
* celerydetp
* rabbitmq-server
* redis
