#!/bin/bash

set -e

echo "Creating data folders"
mkdir -p /ESSArch/log/ \
         /ESSArch/etp/env \
         /ESSArch/data/etp/prepare \
         /ESSArch/data/etp/prepare_reception \
         /ESSArch/data/etp/reception \
         /ESSArch/data/gate/reception \
         /ESSArch/data/epp/ingest \
         /ESSArch/data/epp/cache \
         /ESSArch/data/epp/work \
         /ESSArch/data/epp/disseminations \
         /ESSArch/data/epp/orders \
         /ESSArch/data/epp/verify \
         /ESSArch/data/epp/temp \
         /ESSArch/data/epp/reports/appraisal \
         /ESSArch/data/epp/reports/conversion \
         /ESSArch/data/eta/reception/eft \
         /ESSArch/data/eta/uip \
         /ESSArch/data/eta/work

echo "Apply database migrations"
python manage.py migrate

echo "Installing defaults"
python install/install_default_config.py

echo "Starting server"
python manage.py runserver 0:8000

