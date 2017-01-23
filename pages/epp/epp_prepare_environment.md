---
title: Prepare Environment
tags: [getting_started, troubleshooting]
keywords:
summary: "Prepare Environment"
sidebar: epp_sidebar
permalink: epp_prepare_environment.html
folder: epp
---

## Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile after "ESSArch Core" section:

    ### EPP start
    ##
    export EPP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_EPP
    export PYTHONPATH=$EPP:$PYTHONPATH
    ##
    ### EPP end

[<img align="right" src="images/n.png">](epp_install.html)
{% include links.html %}
