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

if [ ! -f .vscode/settings.json ]; then
    cp .vscode/settings.json.default .vscode/settings.json
fi
if [ ! -f .vscode/extensions.json ]; then
    cp .vscode/extensions.json.default .vscode/extensions.json
fi

echo "Starting server"
python manage.py runserver 0.0.0.0:8000
