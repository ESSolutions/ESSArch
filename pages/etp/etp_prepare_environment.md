---
title: Prepare Environment
tags: [getting_started, troubleshooting]
keywords:
summary: "Prepare Environment"
sidebar: etp_sidebar
permalink: etp_prepare_environment.html
folder: etp
---

## Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile after "ESSArch Core" section:

    ### ETP start
    ##
    export ETP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_TP
    export PYTHONPATH=$ETP:$PYTHONPATH
    ##
    ### ETP end

[<img align="right" src="images/n.png">](etp_install.html)
{% include links.html %}
