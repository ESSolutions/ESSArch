---
title: Prepare Environment
tags: [getting_started, troubleshooting]
keywords:
summary: "Prepare Environment"
sidebar: ec_sidebar
permalink: ec_prepare_environment.html
folder: ec
---

## Create user and group

    Please run the following command as user root.
    # groupadd arch
    # useradd -c "ESSArch System Account" -m -g arch arch

## Set password for arch user

    Please run the following command as user root.
    # passwd arch
    Changing password for user arch.
    New UNIX password: password
    Retype new UNIX password: password

## Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile:

    ### ESSArch Core start
    ##
    export PATH=/ESSArch/pd/python/bin:$PATH:/usr/sbin
    export LANG=en_US.UTF-8
    export LD_LIBRARY_PATH=/ESSArch/pd/python/lib:/ESSArch/pd/libxslt/lib:/ESSArch/pd/libxml/lib:$LD_LIBRARY_PATH
    export EC=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_Core
    export EC_PYTHONPATH=$EC:/ESSArch/config
    export PYTHONPATH=$EC_PYTHONPATH
    export DJANGO_SETTINGS_MODULE=config.settings
    alias log='cd /ESSArch/log'
    ##
    ### ESSArch Core end

## Create installation directory

    Please run the following command as user root.
    # mkdir /ESSArch
    # chown -R arch:arch /ESSArch

[<img align="right" src="images/n.png">](ec_install.html)

{% include links.html %}
