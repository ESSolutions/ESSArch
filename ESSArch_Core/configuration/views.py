"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Core
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from _version import get_versions
import platform
import socket
import sys

from django.db import connection
from django.conf import settings
from django.utils import timezone

try:
    from pip._internal.operations.freeze import freeze as pip_freeze
except ImportError:  # pip < 10.0
    from pip.operations.freeze import freeze as pip_freeze

from sqlite3 import sqlite_version

from ESSArch_Core.configuration.models import (
    Agent,
    ArchivePolicy,
    EventType,
    Parameter,
    Path,
)

from ESSArch_Core.configuration.serializers import (
    AgentSerializer,
    ArchivePolicySerializer,
    EventTypeSerializer,
    ParameterSerializer,
    PathSerializer,
)

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView


class SysInfoView(APIView):
    """
    API endpoint that allows system info to be viewed
    """

    def get_database_info(self):
        vendor = connection.vendor
        version = None

        if vendor == 'mysql':
            version = connection.mysql_version

        if vendor == 'sqlite':
            version = sqlite_version

        if vendor == 'postgresql':
            version = connection.pg_version

        if vendor == 'oracle':
            version = connection.oracle_full_version

        if vendor == 'microsoft':
            version = connection.sql_server_version

        return {'vendor': vendor, 'version': version}

    def get(self, request):
        context = {}
        cwd = settings.BASE_DIR

        # Flags in settings: Their expected  and actual values.
        SETTINGS_FLAGS = [
            ('DEBUG', False),
            ('LANGUAGE_CODE', None),
            ('TIME_ZONE', None),
        ]

        context['python'] = '.'.join(str(x) for x in sys.version_info[:3])
        context['platform'] = platform.platform()
        context['hostname'] = socket.gethostname()
        context['version'] = get_versions()['version']
        context['time_checked'] = timezone.now()
        context['database'] = self.get_database_info()
        context['python_packages'] = pip_freeze()

        context['settings_flags'] = []
        for name, expected in SETTINGS_FLAGS:
            actual_setting = getattr(settings, name, None)
            if expected is not None:
                unexpected = expected != actual_setting
            else:
                unexpected = False
            context['settings_flags'].append({
                'name': name,
                'unexpected': unexpected,
                'actual': actual_setting
            })

        return Response(context)


class EventTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows event types to be viewed or edited.
    """
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer
    pagination_class = None


class AgentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows agents to be viewed or edited.
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer


class ParameterViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows parameters to be viewed or edited.
    """
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer


class PathViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows paths to be viewed or edited.
    """
    queryset = Path.objects.all()
    serializer_class = PathSerializer


class ArchivePolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archive policies to be viewed or edited.
    """
    queryset = ArchivePolicy.objects.all()
    serializer_class = ArchivePolicySerializer
