---
title: Install ESSArch Core
permalink: ec_install.html
keywords: ESSArch Core
sidebar: ec_sidebar
folder: ec
---

## EC installation script

Please download the latest installation package from  [GitHub](https://github.com/ESSolutions/ESSArch_Core/releases/latest)

    Change to user "arch" with the following command.
    # su - arch

    Extract and install the downloaded package.
    [arch@server ~]$ tar xvf ESSArch_Core_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_Core_installer-x.x.x
    [arch@server ~]$ ./install

    The installation of ESSArch is now running and dependent on hardware
    configuration, the installation may take some time. To see details of the
    installation progress please start a new terminal window and run the
    following command.
    [arch@server ~]$ tail -f /ESSArch/install.log

    When installation is finished, search in the log file /ESSArch/install.log
    for any unexpected errors indicating failure of installation of any modules.

## Enable automatic startup at system boot

    Login as root user.

### Enable automatic startup of Apache HTTPD

    Please run the following command as user root.
    # cp /home/arch/ESSArch_Core_installer-x.x.x/extra/esshttpd2.sh /etc/init.d/esshttpd
    # chmod 744 /etc/init.d/esshttpd
    # chkconfig esshttpd on

### Enable automatic startup RabbitMQ

    Please run the following command as user root.
    # chkconfig rabbitmq-server on
    # service rabbitmq-server start

### Enable automatic backup of MySQL / MariaDB

    Please run the following command as user root.
    # cp /ESSArch/config/automysqlbackup/runmysqlbackup /etc/cron.daily/runmysqlbackup
    # chmod 744 /etc/cron.daily/runmysqlbackup

[<img align="right" src="images/n.png">][ec_safety_backup_procedures]

{% include links.html %}
