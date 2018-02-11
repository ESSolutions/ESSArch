---
title: Install ESSArch Tools for Producer
keywords: ESSArch ETP Tools Producer
permalink: etp_install_1_2.html
sidebar: etp_sidebar_1_2
folder: etp_1_2
---

## ETP installation script

Please download the latest installation package from  [GitHub](https://github.com/ESSolutions/ESSArch_Tools_Producer/releases/latest){:target="_blank"}

    Change to user "arch" with the following command.
    # su - arch

    Extract and install the downloaded package.
    [arch@server ~]$ tar xvf ESSArch_TP_installer-x.x.x.tar.gz
    [arch@server ~]$ cd ESSArch_TP_installer-x.x.x
    [arch@server ~]$ ./install

    The installation of ESSArch is now running and dependent on hardware
    configuration, the installation may take some time. To see details of the
    installation progress please start a new terminal window and run the
    following command.
    [arch@server ~]$ tail -f /ESSArch/install_etp.log

    When installation is finished, search in the log file /ESSArch/install_etp.log
    for any unexpected errors indicating failure of installation of any modules.

## Configuring

### Apache httpd configuration

    Edit file /ESSArch/config/httpd-etp.conf and change the configuration entry for
    "ServerName" to same as the hostname of the ESSArch server.

    Add the line "Include /ESSArch/config/httpd-etp.conf" in the file
    /ESSArch/config/httpd.conf

    For test purpose you can use the existing configuration for SSL certificate,
    but for production environment and for maximum security we recommend
    generating your own SSL certificate or if you have your own SSL trusted
    certificate install them in the apache httpd configuration.

### Collect static files to be served by apache httpd

    Please run the following command as user: arch
    [arch@server ~]$ python $ETP/manage.py collectstatic

### ETP configuration

    Path /ESSArch/config contains the configuration files for ESSArch. To change
    the configuration of the ETP, create the /ESSArch/config/local_etp_settings.py
    or update existing file.

    You will also find configuration in the local database tables. To change
    the configuration please login as sysadmin user is ETP and select
    menu MANAGEMENT > Configuration

### RabbitMQ virtual host configuration for ETP

    Add virtual host to RabbitMQ as root user:
    # rabbitmqctl add_user guest guest
    # rabbitmqctl add_vhost etp
    # rabbitmqctl set_permissions -p etp guest ".*" ".*" ".*"

## Database

ESSArch is designed to be RDBMS-independent. However the installation package
is prepared for MySQL/MariaDB and the following instructions assume that you
use MySQL/MariaDB.

### MySQL

Follow the instructions below in order to create the user and tables required
by ETP installation.

    To enable MySQL on CentOS 6 run the following commands as user: root.
    /sbin/chkconfig mysqld on
    /sbin/service mysqld start  
    /usr/bin/mysql_secure_installation

    The MySQL commands listed below can be run within the mysql program, which
    may be invoked as follows.
    # mysql -u root -p

    Create the database. For example, to create a database named "etp", enter.
    mysql> CREATE DATABASE etp DEFAULT CHARACTER SET utf8;

    Set username, password and permissions for the database. For example, to
    set the permissions for user "arkiv" with password "password" on database
    "etp", enter:
    mysql> GRANT ALL ON etp.* TO arkiv@localhost IDENTIFIED BY 'password';

### MariaDB

Follow the instructions below in order to create the user and tables required
by ETP installation.

    To enable MariaDB on CentOS 7 run the following commands as user: root.
    /sbin/chkconfig mariadb on
    /sbin/service mariadb start
    /usr/bin/mysql_secure_installation

    The MySQL commands listed below can be run within the mysql program, which
    may be invoked as follows.
    # mysql -u root -p

    Create the database. For example, to create a database named "etp", enter.
    mysql> CREATE DATABASE etp DEFAULT CHARACTER SET utf8;

    Set username, password and permissions for the database. For example, to
    set the permissions for user "arkiv" with password "password" on
    database "etp", enter:
    mysql> GRANT ALL ON etp.* TO arkiv@localhost IDENTIFIED BY 'password';

### Create default tables in database

    Please run the following command as user: arch
    [arch@server ~]$ python $ETP/manage.py migrate

### Add default configuration data to database

    Please run the following command as user: arch
    [arch@server ~]$ python $ETP/install/install_default_config_etp.py
    [arch@server ~]$ python $EC/ESSArch_Core/install/install_default_config.py

## Enable automatic startup at system boot

    Login as root user and set ETP path variable:
    # export ETP_package='ESSArch_TP_installer-1.2.0'

### Enable workerprocess

    Please run the following commands as root user.
    # cp /home/arch/${ETP_package}/extra/celerydetp.service /usr/lib/systemd/system/
    # systemctl enable celerydetp.service
    # cp /home/arch/${ETP_package}/extra/daphneetp.service /usr/lib/systemd/system/
    # systemctl enable daphneetp.service
    # cp /home/arch/${ETP_package}/extra/wsworkeretp.service /usr/lib/systemd/system/
    # systemctl enable wsworkeretp.service

[<img align="right" src="images/n.png">](etp_running_1_2.html)
{% include links.html %}
