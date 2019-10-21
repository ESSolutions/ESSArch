#!/bin/bash

set -e

essarch settings generate -q --no-overwrite
essarch install -q

echo "Installing defaults"
python ESSArch_Core/install/install_default_config.py

echo "Installing profiles"
python ESSArch_Core/install/install_profiles_se.py

echo "Starting server"
python manage.py runserver 0:8000
