#!/usr/bin/env python
import sys

from ESSArch_Core.config import initialize

if __name__ == "__main__":
    initialize()

from django.core.management import execute_from_command_line  # noqa isort:skip

execute_from_command_line(sys.argv)
