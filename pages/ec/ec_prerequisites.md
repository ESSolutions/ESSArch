---
title: Prerequisites
tags: [getting_started, troubleshooting]
keywords:
summary: "Hardware configuration for server, network and storage architecture is not affected in this guide. Software configurations for server operating systems occur preferably before the installation of ESSArch begins. The installation is expected to be done as user 'root'."
sidebar: ec_sidebar
permalink: ec_prerequisites.html
folder: ec
---

## Supported OS platforms

| **OS** | **Version** | **Note**  |
| --- | --- | --- |
| CentOS / Redhat | 6 (x86\_64) |   |
| CentOS / Redhat | 7 (x86\_64) |   |
| SUSE Linux Enterprise Server | 11 (x86\_64) |   |

(Other Linux and Microsoft operating systems have been tested but are not yet
fully supported, please send us a request with your needs)

## OS Packages

Before installing ESSArch Core you need to verify that the following packages
are installed on your platform

| **Package**                | **Minimum version** | **Note** | **Verified version**         |
|----------------------------|---------------------|----------|------------------------------|
| kernel-devel               | 2.6.x               |          | 2.6.32-504                   |
| sysstat                    | 7.x                 |          | 9.0.4-27                     |
| make                       | 3.81-15             |          | 3.81-20                      |
| patch                      | 2.6.1-1             |          | 2.6-6                        |
| erlang \*\*                | R12B-5.8            |          | R14B-04.3                    |
| gcc                        | 4.1.2               |          | 4.4.7-11                     |
| gcc-c++                    | 4.1.2               |          | 4.4.7-11                     |
| openssl                    | 1.0.1               |          | 1.0.1e-30                    |
| openssl-devel              | 1.0.1               |          | 1.0.1e-30                    |
| openldap                   | 2.3.43              |          | 2.4.39-8                     |
| openldap-devel             | 2.3.43              |          | 2.4.39-8                     |
| mt-st                      | 1.1                 |          | 1.1-5                        |
| mtx                        | 1.2.18              |          | 1.3.12-5                     |
| sg3\_utils                 | 1.25                |          | 1.28-6                       |
| sg3\_utils-libs            | 1.25                |          | 1.28-6                       |
| sg3\_utils-devel           | 1.25                |          | 1.28-6                       |
| mysql                      | 5.0.77              |          | 5.1.73-3                     |
| mysql-server               | 5.0.77              |          | 5.1.73-3                     |
| mysql-devel                | 5.0.77              |          | 5.1.73-3                     |
| mysql-libs                 | 5.0.77              |          | 5.1.73-3                     |
| gnutls                     | 1.4.1               |          | 2.8.5-14                     |
| readline                   | 5.1.3               |          | 6.0-4                        |
| readline-devel             | 5.1.3               |          | 6.0-4                        |
| unixODBC                   | 2.2.11              |          | 2.2.14-14                    |
| unixODBC-devel             | 2.2.11              |          | 2.2.14-14                    |
| freetds                    | 0.64                |          | 0.91-2                       |
| freetds-devel              | 0.64                |          | 0.91-2                       |
| pcre                       | 7.8                 |          | 7.8-6                        |
| pcre-devel                 | 7.8                 |          | 7.8-6                        |
| lzo                        | 2.03-2              |          | 2.03-3.1                     |
| lzo-devel                  | 2.03-2              |          | 2.03-3.1                     |
| xz                         | 4.999.9-0.1         |          | 4.999.9-0.5.beta.20091007git |
| bzip2-devel (libbz2-devel) | 1.0.5-5             |          | 1.0.5-7                      |
| libffi-devel               | 3.0.5-3.2           |          | 3.0.5-3.2                    |
| sqlite-devel               | 3.6                 |          | 3.6.20-1                     |
| rabbitmq-server            | 3.3.1               |          | 3.3.5-28                     |
| redis                      | 2.8.0               |          | 2.8.19-2                     |

\*\* CentOS 6 require extra package: [epel-release](https://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm)

    Install this epel repository before you try to install erlang package
    # yum install epel-release-latest-6.noarch.rpm

\*\* CentOS 7 require extra package: [epel-release](https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm)

    Install this epel repository before you try to install erlang package
    # yum install epel-release-latest-7.noarch.rpm

\*\* SUSE require extra package: [epel-release](http://download.opensuse.org/repositories/devel:/languages:/erlang/)

    Install erlang-epmd without dependencies since it requires erlang and vice
    versa erlang requires erlang-epmd
    wget http://download.opensuse.org/repositories/devel:/languages:/erlang/SLE_11_SP4/x86_64/erlang-18.3-12.1.x86_64.rpm
    wget http://download.opensuse.org/repositories/devel:/languages:/erlang/SLE_11_SP4/x86_64/erlang-epmd-18.3-12.1.x86_64.rpm
    rpm -i --nodeps erlang-epmd-18.3-12.1.x86_64.rpm
    rpm -i erlang-18.3-12.1.x86_64.rpm

## Installing packages

### [Redis](https://redis.io){:target="_blank"} (new in 1.1.0)

#### CentOS

    Install
    # yum install redis

    Start service
    # systemctl start redis.service

    Start service at system boot
    # systemctl enable redis.service


**TIP:** If you extract the contents of the installation package for
[ESSArch Core](https://github.com/ESSolutions/ESSArch_Core/releases/latest){:target="_blank"} and look in the directory folder "extra", there is help script to
install required OS package.

[<img align="right" src="images/n.png">](ec_prepare_environment.html)
{% include links.html %}
