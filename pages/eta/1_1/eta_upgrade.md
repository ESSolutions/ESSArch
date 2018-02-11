---
title: Upgrade ESSArch Tools Archive
keywords: ESSArch Tools Archive
permalink: eta_upgrade_1_1.html
sidebar: eta_sidebar_1_1
folder: eta_1_1
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

### Upgrade database schema

    [arch@server ~]$ python $ETA/manage.py migrate

{% include important.html content="
When upgrading **you must** ensure that the storage engine is correct for the
database. In MySQL the storage engine for previously created tables can be
found by the following command:
" %}

    SELECT table_schema, table_name, engine FROM INFORMATION_SCHEMA.TABLES where table_schema = ”eta”;

{% include important.html content="

If you are not using the default storage engine (InnoDB on MySQL) then it must
be specified in your configuration file:

" %}

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'eta',
            'USER': 'arkiv',
            'PASSWORD': 'password',
            'HOST': '',
            'PORT': '',
            'OPTIONS': {
               #"init_command": "SET storage_engine=MyISAM",  # MySQL (<= 5.5.2)
               "init_command": "SET default_storage_engine=MyISAM",  # MySQL (>= 5.5.3)
            }
        }
    }

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
