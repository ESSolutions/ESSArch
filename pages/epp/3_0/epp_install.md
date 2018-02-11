---
title: Install ESSArch Preservation Platform
keywords: ESSArch EPP Preservation Platform
permalink: epp_install_3_0.html
sidebar: epp_sidebar_3_0
folder: epp_3_0
---

## EPP installation script

Please download the latest installation package from  [GitHub](https://github.com/ESSolutions/ESSArch_EPP/releases/latest){:target="_blank"}

    Change to user "arch" with the following command.
    # su - arch

    Extract and install the downloaded package.
    [arch@server ~]$ tar xvf ESSArch_PP_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_PP_installer-x.x.x
    [arch@server ~]$ ./install

    The installation of ESSArch is now running and dependent on hardware
    configuration, the installation may take some time. To see details of the
    installation progress please start a new terminal window and run the
    following command.
    [arch@server ~]$ tail -f /ESSArch/install_epp.log

    When installation is finished, search in the log file /ESSArch/install_epp.log
    for any unexpected errors indicating failure of installation of any modules.

## Configuring

### Apache httpd configuration

    Edit file /ESSArch/config/httpd-epp.conf and change the configuration entry for
    "ServerName" to same as the hostname of the ESSArch server.

    Add the line "Include /ESSArch/config/httpd-epp.conf" in the file
    /ESSArch/config/httpd.conf

    For test purpose you can use the existing configuration for SSL certificate,
    but for production environment and for maximum security we recommend
    generating your own SSL certificate or if you have your own SSL trusted
    certificate install them in the apache httpd configuration.

### Collect static files to be served by apache httpd

    Please run the following command as user: arch
    [arch@server ~]$ python $EPP/manage.py collectstatic

### EPP configuration

    Path /ESSArch/config contains the configuration files for ESSArch. To change
    the configuration of the EPP, create the /ESSArch/config/local_settings.py
    or update existing file.

    You will also find configuration in the local database tables. To change
    the configuration please login as sysadmin user is EPP and select
    menu MANAGEMENT > Configuration

## Database

ESSArch is designed to be RDBMS-independent. However the installation package
is prepared for MySQL/MariaDB and the following instructions assume that you
use MySQL/MariaDB.

### MySQL

Follow the instructions below in order to create the user and tables required
by EPP installation.

    To enable MySQL on CentOS 6 run the following commands as user: root.
    /sbin/chkconfig mysqld on
    /sbin/service mysqld start  
    /usr/bin/mysql_secure_installation

    The MySQL commands listed below can be run within the mysql program, which
    may be invoked as follows.
    # mysql -u root -p

    Create the database. For example, to create a database named "essarch", enter.
    mysql> CREATE DATABASE epp DEFAULT CHARACTER SET utf8;

    Set username, password and permissions for the database. For example, to
    set the permissions for user "arkiv" with password "password" on database
    "essarch", enter:
    mysql> GRANT ALL ON epp.* TO arkiv@localhost IDENTIFIED BY 'password';

### MariaDB

Follow the instructions below in order to create the user and tables required
by EPP installation.

    To enable MariaDB on CentOS 7 run the following commands as user: root.
    /sbin/chkconfig mariadb on
    /sbin/service mariadb start
    /usr/bin/mysql_secure_installation

    The MySQL commands listed below can be run within the mysql program, which
    may be invoked as follows.
    # mysql -u root -p

    Create the database. For example, to create a database named "essarch", enter.
    mysql> CREATE DATABASE epp DEFAULT CHARACTER SET utf8;

    Set username, password and permissions for the database. For example, to
    set the permissions for user "arkiv" with password "password" on
    database "essarch", enter:
    mysql> GRANT ALL ON epp.* TO arkiv@localhost IDENTIFIED BY 'password';

### Create default tables in database

    Please run the following command as user: arch
    [arch@server ~]$ python $EPP/manage.py migrate

### Add default configuration data to database

Use only this default configuration for test purpose, do not install this
default configuration in production.
Replace XX with country specific profiles: se, no or eark

    Please run the following command as user: arch
    [arch@server ~]$ python $EPP/install/install_default_config_epp.py
    [arch@server ~]$ python $EPP/install/install_profiles_epp_XX.py
    [arch@server ~]$ python $EC/ESSArch_Core/install/install_default_config.py

#### For production/custom installation

For production environment you should first make a copy of this
configuration file and update for example site_profile, site_name.

    [arch@server ~]$ cp $EPP/install/install_default_config_epp.py /home/arch/install_config_custom.py

Update /home/arch/install_config_custom.py

Install configuration:

    [arch@server ~]$ python /home/arch/install_config_custom.py

## Enable automatic startup at system boot

    Login as root user and set EPP path variable:
    # export EPP_package='ESSArch_PP_installer-3.0.0'

### Enable workerprocess

    Please run the following commands as root user.
    # cp /home/arch/${EPP_package}/extra/celerydepp.service /usr/lib/systemd/system/
    # systemctl enable celerydepp.service
    # cp /home/arch/${EPP_package}/extra/celerybeatepp.service /usr/lib/systemd/system/
    # systemctl enable celerybeatepp.service
    # cp /home/arch/${EPP_package}/extra/daphneepp.service /usr/lib/systemd/system/
    # systemctl enable daphneepp.service
    # cp /home/arch/${EPP_package}/extra/wsworkerepp.service /usr/lib/systemd/system/
    # systemctl enable wsworkerepp.service

[<img align="right" src="images/n.png">](epp_running_3_0.html)
{% include links.html %}
