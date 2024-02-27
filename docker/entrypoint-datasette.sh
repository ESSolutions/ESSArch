#!/bin/bash

set -e

echo "Starting datasette server"
datasette -h 0.0.0.0 -p 8001
