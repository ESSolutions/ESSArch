# ETP (ESSArch tools producer)

SIP packaging and delivery tools for user producer.

# Installation Guide

## Prerequisites

Hardware configuration for server, network and storage architecture is not affected in this guide. Software configurations for server operating systems occur preferably before the installation of ESSArch begins. The installation is expected to be done as user 'root'.

## Supported OS platforms

| **OS** | **Version** |   |
| --- | --- | --- |
| CentOS | 5.5 (x86\_64) |   |
| CentOS | 6.4 (x86\_64) | CentOS release 6.6 (Final) |
| Redhat Enterprise Server | 5 (x86\_64) |   |
| SUSE Linux Enterprise Server | 10 (x86\_64) |   |
| SUSE Linux Enterprise Server | 11 (x86\_64) SP3 |   |
| Fedora | 11 (x86\_64) |   |

## OS Packages

Before installing ESSArch you need to verify that the following packages are installed on your platform

| **Package** | **Minimum version** | **Note** | **Verified version** |
| --- | --- | --- | --- |
| kernel-devel | 2.6.x |   | kernel-devel-2.6.32-504.el6.x86\_64 |
| sysstat | 7.x |   | sysstat-9.0.4-27.el6.x86\_64 |
| make | 3.81-15 |   | make-3.81-20.el6.x86\_64 |
| patch | 2.6.1-1 |   | patch-2.6-6.el6.x86\_64 |
| erlang \*\* | R12B-5.8 |   | erlang-R14B-04.3.el6.x86\_64 |
| gcc | 4.1.2 |   | gcc-4.4.7-11.el6.x86\_64 |
| gcc-c++ | 4.1.2 |   | gcc-c++-4.4.7-11.el6.x86\_64 |
| ppenssl | 0.9.8 |   | openssl-1.0.1e-30.el6.x86\_64 |
| openssl-devel | 0.9.8 |   | openssl-devel-1.0.1e-30.el6.x86\_64 |
| openldap | 2.3.43 |   | openldap-2.4.39-8.el6.x86\_64 |
| openldap-devel | 2.3.43 |   | openldap-devel-2.4.39-8.el6.x86\_64 |
| mt-st | 0.9b |   | mt-st-1.1-5.el6.x86\_64 |
| mtx | 1.2.18 |   | mtx-1.3.12-5.el6.x86\_64 |
| sg3\_utils | 1.25 |   | sg3\_utils-1.28-6.el6.x86\_64 |
| sg3\_utils-libs | 1.25 |   | sg3\_utils-libs-1.28-6.el6.x86\_64 |
| sg3\_utils-devel | 1.25 |   | sg3\_utils-devel-1.28-6.el6.x86\_64 |
| mysql | 5.0.77 |   | mysql-5.1.73-3.el6\_5.x86\_64 |
| mysql-server | 5.0.77 |   | mysql-server-5.1.73-3.el6\_5.x86\_64 |
| mysql-devel | 5.0.77 |   | mysql-devel-5.1.73-3.el6\_5.x86\_64 |
| mysql-libs | 5.0.77 |   | mysql-libs-5.1.73-3.el6\_5.x86\_64 |
| gnutls | 1.4.1 |   | gnutls-2.8.5-14.el6\_5.x86\_64 |
| readline | 5.1.3 |   | readline-6.0-4.el6.x86\_64 |
| readline-devel | 5.1.3 |   | readline-devel-6.0-4.el6.x86\_64 |
| unixODBC | 2.2.11 |   | unixODBC-2.2.14-14.el6.x86\_64 |
| unixODBC-devel | 2.2.11 |   | unixODBC-devel-2.2.14-14.el6.x86\_64 |
| freetds | 0.64 |   | freetds-0.91-2.el6.x86\_64 |
| freetds-devel | 0.64 |   | freetds-devel-0.91-2.el6.x86\_64 |
| pcre | 7.8 |   | pcre-7.8-6.el6.x86\_64 |
| pcre-devel | 7.8 |   | pcre-devel-7.8-6.el6.x86\_64 |
| lzo | 2.03-2 |   | lzo-2.03-3.1.el6\_5.1.x86\_64 |
| lzo-devel | 2.03-2 |   | lzo-devel-2.03-3.1.el6\_5.1.x86\_64 |
| xz | 4.999.9-0.1 |   | xz-4.999.9-0.5.beta.20091007git.el6.x86\_64 |
| bzip2-devel (libbz2-devel) | 1.0.5-5 |   | bzip2-devel-1.0.5-7.el6\_0.x86\_64 |
| libffi-devel | 3.0.5-3.2 |   | libffi-devel.x86\_64 0:3.0.5-3.2.el6 |
| sqlite-devel | 3.6 |   | 3.6.20-1.el6.x86\_64 |

\*\* Centos require extra package: [epel-release](http://ftp.acc.umu.se/mirror/fedora/epel/6/i386/epel-release-6-8.noarch.rpm)

## Prepare Environment

### Create user and group

Don't forget to create /home/arch

    Please run the following command as user root.
    # groupadd arch
    # useradd -c "ESSArch System Account" -m -g arch arch

### Set password for arch user

    Please run the following command as user root.
    # passwd arch
    Changing password for user arch.
    New UNIX password: password
    Retype new UNIX password: password

### Customize user environment for arch user

Add the following rows to /home/arch/.bash_profile:

    ### ESSArch start
    ##
    export PATH=/ESSArch/pd/python/bin:$PATH:/usr/sbin
    export LANG=en_US.UTF-8
    export LD_LIBRARY_PATH=/ESSArch/pd/python/lib:/ESSArch/pd/libxslt/lib:/ESSArch/pd/libxml/lib:$LD_LIBRARY_PATH
    export ETP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_TP
    export PYTHONPATH=$ETP:/ESSArch/config
    export DJANGO_SETTINGS_MODULE=config.settings
    alias bin='cd /ESSArch/bin'
    alias log='cd /ESSArch/log'
    ##
    ### ESSArch end

### Create installation directory

    Please run the following command as user root.
    # mkdir /ESSArch
    # chown -R arch:arch /ESSArch

## Installation

### ETP installation script

    Change to user "arch" with the following command.
    # su  arch

    Download and extract ESSArch_TP_install tarfile.
    [arch@server ~]$ wget http://xxx.xxx.xxx.xxx/ESSArch_TP_installer_xxxxxxxxxxxx.tar.gz
    [arch@server ~]$ tar xvf ESSArch_TP_installer_xxxxxxxxxxxx.tar.gz
    [arch@server ~]$ cd ESSArch_TP_installer
    [arch@server ~]$ ./install
    
    The installation of ESSArch is now running and dependent on hardware configuration, the installation may take some time. To see details of the installation progress please start a new terminal window and run the following command.
    [arch@server ~]$ tail f /ESSArch/install.log
    
    When installation is finished, search in the log file /ESSArch/install.log for any unexpected errors indicating failure of installation of any modules.

### Installation of Advanced Message Queuing Protocol

ESSArch is designed to be AMQP (Advanced Message Queuing Protocol) independent. However the installation package is prepared for RabbitMQ and the following instructions assume that you use RabbitMQ.

Follow the instructions below in order to install RabbitMQ required by ESSArch.

    Please run the following commands as root user.
    # rpm i /ESSArch/install/packages/rabbitmq-server.rpm
    # chkconfig rabbitmq-server on
    # service rabbitmq-server start

If startup failed and you see an error message in /var/log/rabbitmq/startup_log  after a minute or so like:

ERROR: epmd error for host "yourhostname": timeout (timed out)_

Then you need to update your /etc/hosts file to add your hostname to the list of localhost:

127.0.0.1    yourhostname

## Configuring

### Apache httpd configuration

    Edit file /ESSArch/config/httpd-etp.conf and change the configuration entry for "ServerName" to same as the hostname of the ESSArch server.

    For test purpose you can use the existing configuration for SSL certificate, but for production environment and for maximum security we recommend generating your own SSL certificate or if you have your own SSL trusted certificate install them in the apache httpd configuration.

### ESSArch configuration

    In /ESSArch/config you will find all the configuration files for ESSArch. The main configuration file for ESSArch WEB GUI is local_etp_settings.py.
    
    For ESSArch you will find the configuration in the local database tables. To change the configuration please login as admin user is ETP and select menu MANAGEMENT > Configuration

## Database

ESSArch is designed to be RDBMS-independent. 

### Create default tables in database

    Please run the following command as user: arch
    [arch@server ~]$ python $ETP/manage.py migrate

## Add default configuration data to database

Use only this default configuration for test purpose, do not install this default configuration in production.

For production environment you should first make a copy of this configuration file and update for example site_profile, site_name. After you done all your updates you install it.

    Please run the following command as user: arch
    [arch@server ~]$ python $ETP/install/install_config_etp.py

### For production/custom installation

    [arch@server ~]$ cp $ETP/install/install_config_etp.py /home/arch/install_config_etp_custom.py

Update /home/arch/install_config_etp_custom.py

Install configuration:
    
    [arch@server ~]$ python /home/arch/install_config_etp_custom.py

## Add profile configuration data to database

    Please run the following command as user: arch
    [arch@server ~]$ python $ETP/install/install_SA_Profile_NO_etp.py

## Enable automatic startup at system boot

    Login as root user and set ETP path variable:
    # export ETP=/ESSArch/pd/python/lib/python2.7/site-packages/ESSArch_TP

### Enable workerprocess

    Please run the following commands as root user.
    # cp $ETP/extra/celeryd.sh /etc/init.d/celeryd
    # chmod 744 /etc/init.d/celeryd
    # chkconfig celeryd on
    # cp $ETP/extra/celerybeat.sh /etc/init.d/celerybeat
    # chmod 744 /etc/init.d/celerybeat
    # chkconfig celerybeat on

### Enable automatic startup of Apache HTTPD

    Please run the following command as user root.
    # cp $ETP/extra/httpd.sh /etc/init.d/httpd
    # chmod 744 /etc/init.d/httpd
    # chkconfig httpd on

# Running the ETP Server

## Start ETP server

Note that a startup or shutdown of ETP should always be controlled.

    Please run the following command as user root to start ETP.
    # service celeryd start
    # service celerybeat start
    # service httpd start

## Stop ETP server

    Please run the following command as user root to stop ETP.
    # service httpd stop
    # service celeryd stop
    # service celerybeat stop

## Start ETP WEB interface

Start your preferable web browser and connect to ETP Server name or IP address.

URL: [https://xxxxxxxx](https://xxxxxxxx)

By default, for test purpose, the installation has configured the following users:

| **Username** | **Password** | **Role/Permissions** |
| --- | --- | --- |
| usr1 | usr1 | prepare, create, submit |
| admin | admin | admin |

## Important files to backup

Important data in ESSArch to backup is the configuration, log files and database. All areas which are mounted from external file servers should be backed up.

Everything in the file area /ESSArch should be backed up before and after configuration changes or changes in ESSArch system installation, for example when upgrading and software patches.

Areas that need to be backed up to an external "backup system" daily is the following:

- --/ESSArch/etp
- --/ESSArch/backups_mysql
- --/ESSArch/config
- --/ESSArch/log
- --/ESSArch/data

##Events and log information

Different types of events are logged both in physical files and tables in ESSArch database. Log entries are tagged with the log level - Debug, Critical, Error, Warning, Info. These log levels can be felt by the ETP's system logs:

/ESSArch/log
/ESSArch/log/celerybeat.log
/ESSArch/log/celery_worker1.log
/ESSArch/log/httpd_access.log
/ESSArch/log/httpd_error.log
/ESSArch/log/httpd_ssl_request.log

# Service och support

Service and support on ETP is regulated in maintenance contract with ES Solutions AB. A case is registered on the support portal http://projects.essolutions.se
