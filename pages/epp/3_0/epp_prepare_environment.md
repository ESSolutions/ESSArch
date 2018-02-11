---
title: Prepare Environment
tags: [getting_started, troubleshooting]
keywords:
summary: "Prepare Environment"
sidebar: epp_sidebar_3_0
permalink: epp_prepare_environment_3_0.html
folder: epp_3_0
---

## Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile after "ESSArch Core" section:

    ### EPP start
    ##
    export EPP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_PP
    export PYTHONPATH=$EPP:$EC_PYTHONPATH
    alias env_epp='export PYTHONPATH=$EPP:$EC_PYTHONPATH;cd $EPP'
    ##
    ### EPP end

**Note:** If you install multiple ESSArch products such as ETP, ETA or the EPP on the same server, you must adapt PYTHONPATH so that only one product is used at a time. As an alternative, you can run the alias env_etp, env_eta or env_epp that configure PYTHONPATH for each product before you is performing operations.

[<img align="right" src="images/n.png">](epp_install_3_0.html)
{% include links.html %}
