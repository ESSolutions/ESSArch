#!/bin/bash

set -e

essarch settings generate --debug -q --no-overwrite
essarch mimetypes generate -q --no-overwrite
essarch install -q
mkdir -p /ESSArch/config/essarch

echo "Installing profiles"
python ESSArch_Core/install/install_sa_profiles.py se
#python ESSArch_Core/install/install_sa_profiles.py no
python ESSArch_Core/install/install_sa_profiles.py eark

echo "Starting server"
python manage.py runserver 0:8000
