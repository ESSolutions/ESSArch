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

| **Package** | **Minimum version** | **Note** | **Verified version** |
| --- | --- | --- | --- |
| kernel-devel | 2.6.x |   | kernel-devel-2.6.32-504.el6.x86\_64 |
| sysstat | 7.x |   | sysstat-9.0.4-27.el6.x86\_64 |
| make | 3.81-15 |   | make-3.81-20.el6.x86\_64 |
| patch | 2.6.1-1 |   | patch-2.6-6.el6.x86\_64 |
| erlang \*\* | R12B-5.8 |   | erlang-R14B-04.3.el6.x86\_64 |
| gcc | 4.1.2 |   | gcc-4.4.7-11.el6.x86\_64 |
| gcc-c++ | 4.1.2 |   | gcc-c++-4.4.7-11.el6.x86\_64 |
| openssl | 1.0.1 |   | openssl-1.0.1e-30.el6.x86\_64 |
| openssl-devel | 1.0.1 |   | openssl-devel-1.0.1e-30.el6.x86\_64 |
| openldap | 2.3.43 |   | openldap-2.4.39-8.el6.x86\_64 |
| openldap-devel | 2.3.43 |   | openldap-devel-2.4.39-8.el6.x86\_64 |
| mt-st | 1.1 |   | mt-st-1.1-5.el6.x86\_64 |
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
| rabbitmq-server | 3.3.1 |   | rabbitmq-server-3.3.5-28.el7.noarch |

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

**TIP:** If you extract the contents of the installation package for
[ESSArch Core](https://github.com/ESSolutions/ESSArch_Core/releases/latest){:target="_blank"} and look in the directory folder "extra", there is help script to
install required OS package.

[<img align="right" src="images/n.png">][ec_prepare_environment]
{% include links.html %}
