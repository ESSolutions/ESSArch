---
title: Prepare Environment
tags: [getting_started, troubleshooting]
keywords:
summary: "Prepare Environment"
sidebar: eta_sidebar
permalink: eta_prepare_environment.html
folder: eta
---

## Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile after "ESSArch Core" section:

    ### ETA start
    ##
    export ETA=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_TA
    export PYTHONPATH=$ETA:$PYTHONPATH
    ##
    ### ETA end

[<img align="right" src="images/n.png">](eta_install.html)
{% include links.html %}
