---
title: Upgrade ESSArch Core
keywords: ESSArch Core
permalink: ec_upgrade_1_1.html
sidebar: ec_sidebar_1_1
folder: ec_1_1
---

## Stop services
* essarch
* esshttpd
* celeryd
* celerybeat
* celerydepp
* celerybeatepp
* celerydeta
* celerydetp
* daphneepp
* daphneetp
* daphneeta
* wsworkerepp
* wsworkeretp
* wsworkereta

## Verify that a backup of the database exists at `/ESSArch/backup`

## Move old installation

    # cd /ESSArch
    # mkdir old
    # mv config install install*.log pd old/

## Install new ESSArch_Core
    # su - arch
    [arch@server ~]$ tar xvf ESSArch_Core_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_Core_installer-x.x.x
    [arch@server ~]$ ./install


## Compare and restore configuration files at `/ESSArch/config` from `old` directory
    # diff -qr /ESSArch/config old

## Start services

* essarch
* celeryd
* celerybeat
* celerydepp
* celerybeatepp
* celerydeta
* celerydetp
* daphneepp
* daphneetp
* daphneeta
* wsworkerepp
* wsworkeretp
* wsworkereta
* esshttpd
