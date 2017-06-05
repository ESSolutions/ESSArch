---
title: Upgrade ESSArch Core
permalink: ec_upgrade.html
keywords: ESSArch Core
sidebar: ec_sidebar
folder: ec
---

## Stop services
* essarch
* esshttpd
* celeryd
* celerybeat
* celerydeta
* celerydetp
* rabbitmq-server
* redis

## Verify that a backup of the database exists at `/ESSArch/backup`

## Move old installation

    # cd /ESSArch
    # mkdir old
    # mv config install install*.log pd old/

## Install, as arch, new ESSArch_Core
    # su - arch
    [arch@server ~]$ tar xvf ESSArch_Core_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_Core_installer-x.x.x
    [arch@server ~]$ ./install


## Compare and restore configuration files at `/ESSArch/config` from `old` directory
    # diff -qr /ESSArch/config old

## Start services

* essarch
* esshttpd
* celeryd
* celerybeat
* celerydeta
* celerydetp
* rabbitmq-server
* redis
