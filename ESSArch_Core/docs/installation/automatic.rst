.. _installation-automatic:

**********************
Automatic installation
**********************

If you are installing on CentOS/RedHat or OpenSUSE/SLES, and have access to the root
user then there is a script available that automates the installation for you:


Run the following as root

.. code-block:: bash

    $ wget https://www.essarch.org/download/essarch_download
    $ sh essarch_download /ESSArch_setup
    $ /ESSArch_setup/install.sh


This will download, configure, install and start ESSArch and all its
dependencies. Answer the prompts and when the installation is done you will
have a running ESSArch environment accessible at https://hostname
