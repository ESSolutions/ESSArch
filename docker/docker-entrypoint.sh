#!/bin/bash

echo "Apply database migrations"
python manage.py migrate

echo "Installing defaults"
python install/install_default_config.py

echo "Starting server"
python manage.py runserver 0:8000

