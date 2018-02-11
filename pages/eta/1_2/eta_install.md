---
title: Install ESSArch Tools for Archive
keywords: ESSArch ETA Tools Archive
permalink: eta_install_1_2.html
sidebar: eta_sidebar_1_2
folder: eta_1_2
---

## ETA installation script

Please download the latest installation package from  [GitHub](https://github.com/ESSolutions/ESSArch_Tools_Archive/releases/latest){:target="_blank"}

    Change to user "arch" with the following command.
    # su - arch

    Extract and install the downloaded package.
    [arch@server ~]$ tar xvf ESSArch_TA_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_TA_installer-x.x.x
    [arch@server ~]$ ./install

    The installation of ESSArch is now running and dependent on hardware
    configuration, the installation may take some time. To see details of the
    installation progress please start a new terminal window and run the
    following command.
    [arch@server ~]$ tail -f /ESSArch/install_eta.log

    When installation is finished, search in the log file /ESSArch/install_eta.log
    for any unexpected errors indicating failure of installation of any modules.

## Configuring

### Apache httpd configuration

    Edit file /ESSArch/config/httpd-eta.conf and change the configuration entry for
    "ServerName" to same as the hostname of the ESSArch server.

    Add the line "Include /ESSArch/config/httpd-eta.conf" in the file
    /ESSArch/config/httpd.conf

    For test purpose you can use the existing configuration for SSL certificate,
    but for production environment and for maximum security we recommend
    generating your own SSL certificate or if you have your own SSL trusted
    certificate install them in the apache httpd configuration.

### Collect static files to be served by apache httpd

    Please run the following command as user: arch
    [arch@server ~]$ python $ETA/manage.py collectstatic

### ETA configuration

    Path /ESSArch/config contains the configuration files for ESSArch. To change
    the configuration of the ETA, create the /ESSArch/config/local_eta_settings.py
    or update existing file.

    You will also find configuration in the local database tables. To change
    the configuration please login as sysadmin user is ETA and select
    menu MANAGEMENT > Configuration

### RabbitMQ virtual host configuration for ETA

    Add virtual host to RabbitMQ as root user:
    # rabbitmqctl add_user guest guest
    # rabbitmqctl add_vhost eta
    # rabbitmqctl set_permissions -p eta guest ".*" ".*" ".*"

## Database

ESSArch is designed to be RDBMS-independent. However the installation package
is prepared for MySQL/MariaDB and the following instructions assume that you
use MySQL/MariaDB.

### MySQL

Follow the instructions below in order to create the user and tables required
by ETA installation.

    To enable MySQL on CentOS 6 run the following commands as user: root.
    /sbin/chkconfig mysqld on
    /sbin/service mysqld start  
    /usr/bin/mysql_secure_installation

    The MySQL commands listed below can be run within the mysql program, which
    may be invoked as follows.
    # mysql -u root -p

    Create the database. For example, to create a database named "eta", enter.
    mysql> CREATE DATABASE eta DEFAULT CHARACTER SET utf8;

    Set username, password and permissions for the database. For example, to
    set the permissions for user "arkiv" with password "password" on database
    "eta", enter:
    mysql> GRANT ALL ON eta.* TO arkiv@localhost IDENTIFIED BY 'password';

### MariaDB

Follow the instructions below in order to create the user and tables required
by ETA installation.

    To enable MariaDB on CentOS 7 run the following commands as user: root.
    /sbin/chkconfig mariadb on
    /sbin/service mariadb start
    /usr/bin/mysql_secure_installation

    The MySQL commands listed below can be run within the mysql program, which
    may be invoked as follows.
    # mysql -u root -p

    Create the database. For example, to create a database named "eta", enter.
    mysql> CREATE DATABASE eta DEFAULT CHARACTER SET utf8;

    Set username, password and permissions for the database. For example, to
    set the permissions for user "arkiv" with password "password" on
    database "eta", enter:
    mysql> GRANT ALL ON eta.* TO arkiv@localhost IDENTIFIED BY 'password';

### Create default tables in database

    Please run the following command as user: arch
    [arch@server ~]$ python $ETA/manage.py migrate

### Add default configuration data to database

    Please run the following command as user: arch
    [arch@server ~]$ python $ETA/install/install_default_config_eta.py
    [arch@server ~]$ python $EC/ESSArch_Core/install/install_default_config.py

## Enable automatic startup at system boot

    Login as root user and set ETA path variable:
    # export ETA_package='ESSArch_TA_installer-1.2.0'

### Enable workerprocess

    Please run the following commands as root user.
    # cp /home/arch/${ETA_package}/extra/celerydeta.service /usr/lib/systemd/system/
    # systemctl enable celerydeta.service
    # cp /home/arch/${ETA_package}/extra/daphneeta.service /usr/lib/systemd/system/
    # systemctl enable daphneeta.service
    # cp /home/arch/${ETA_package}/extra/wsworkereta.service /usr/lib/systemd/system/
    # systemctl enable wsworkereta.service

[<img align="right" src="images/n.png">](eta_running_1_2.html)
{% include links.html %}
