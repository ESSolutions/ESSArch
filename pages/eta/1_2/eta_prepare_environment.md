---
title: Prepare Environment
tags: [getting_started, troubleshooting]
keywords:
summary: "Prepare Environment"
sidebar: eta_sidebar_1_2
permalink: eta_prepare_environment_1_2.html
folder: eta_1_2
---

## Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile after "ESSArch Core" section:

    ### ETA start
    ##
    export ETA=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_TA
    export PYTHONPATH=$ETA:$EC_PYTHONPATH
    alias env_eta='export PYTHONPATH=$ETA:$EC_PYTHONPATH;cd $ETA'
    ##
    ### ETA end

**Note:** If you install multiple ESSArch products such as ETP, ETA or the EPP on the same server, you must adapt PYTHONPATH so that only one product is used at a time. As an alternative, you can run the alias env_etp, env_eta or env_epp that configure PYTHONPATH for each product before you is performing operations.

[<img align="right" src="images/n.png">](eta_install_1_2.html)
{% include links.html %}
