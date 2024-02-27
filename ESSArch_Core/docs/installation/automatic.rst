.. _installation-automatic:

**********************
Automatic installation
**********************

If you are installing on Ubuntu, Debian, RHEL, OpenSUSE or SLES, and have access to the root
user then there is a script available that automates the installation for you:


Run the following as root to install "nightly build" (Recomended for test installation)

.. code-block:: bash

    $ wget https://www.essarch.org/download/essarch_download
    $ bash essarch_download dev /ESSArch_setup
    $ /ESSArch_setup/install.sh

Run the following as root to install "latest stable" (Recomended for production installation)

.. code-block:: bash

    $ wget https://www.essarch.org/download/essarch_download
    $ bash essarch_download latest /ESSArch_setup
    $ /ESSArch_setup/install.sh

This will download, configure, install and start ESSArch and all its
dependencies. Answer the prompts and when the installation is done you will
have a running ESSArch environment accessible at https://hostname
