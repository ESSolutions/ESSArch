#!/bin/bash

set -e

essarch settings generate -q --no-overwrite
essarch install -q

echo "Installing defaults"
python ESSArch_Core/install/install_default_config.py

echo "Starting server"
python manage.py runserver 0:8000

