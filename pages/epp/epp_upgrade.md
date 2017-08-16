---
title: Upgrade ESSArch Preservation Platform
permalink: epp_upgrade.html
keywords: ESSArch Preservation Platform
sidebar: epp_sidebar
folder: epp
---

## Stop services
* essarch
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


### Collect static files to be served by apache httpd

    [arch@server ~]$ python $EPP/manage.py collectstatic

### Upgrade database schema

    [arch@server ~]$ python $EPP/manage.py migrate

{% include important.html content="
When upgrading **you must** ensure that the storage engine is correct for the
database. In MySQL the storage engine for previously created tables can be
found by the following command:
" %}

    SELECT table_schema, table_name, engine FROM INFORMATION_SCHEMA.TABLES where table_schema = ”essarch”;

{% include important.html content="

If you are not using the default storage engine (MyISAM on MySQL) then it must
be specified in your configuration file:

" %}

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'essarch',
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
Use only this default configuration for test purpose, do not install this default configuration in production.


*Note: Before running the script, compare it with the data currently in the database and see if running it is necessary*

    [arch@server ~]$ python $EPP/extra/install_config.py

#### For production/custom installation
If you have made a custom configuration you should compare your configuration
with the new default configuration and see if there is anything new

    [arch@server ~]$ diff $EPP/extra/install_config.py /home/arch/install_config_custom.py

If there is anything new in the default you should copy this to your custom installation file and install it

    [arch@server ~]$ cp $EPP/extra/install_config.py /home/arch/install_config_custom.py
    [arch@server ~]$ python /home/arch/install_config_custom.py

## Compare and restore configuration files at `/ESSArch/config` from `old` directory
    # diff -qr /ESSArch/config old

## Start services

* essarch
* esshttpd
* celeryd
* celerybeat
* rabbitmq-server
