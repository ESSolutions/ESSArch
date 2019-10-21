#!/bin/bash -e

while ! nc -z $1 $2; do echo "waiting for '$1' on port '$2'..."; sleep 1; done;
