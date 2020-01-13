"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch
    Copyright (C) 2005-2019 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

import logging
import platform
import socket
import sys
from sqlite3 import sqlite_version

import distro
from celery import current_app
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django_redis import get_redis_connection
from elasticsearch.exceptions import ElasticsearchException
from elasticsearch_dsl.connections import get_connection as get_es_connection
from redis.exceptions import RedisError
from rest_framework import filters, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ESSArch_Core._version import get_versions
from ESSArch_Core.api.filters import SearchFilter, string_to_bool
from ESSArch_Core.configuration.filters import EventTypeFilter
from ESSArch_Core.configuration.models import (
    EventType,
    Parameter,
    Path,
    Site,
    StoragePolicy,
)
from ESSArch_Core.configuration.serializers import (
    EventTypeSerializer,
    ParameterSerializer,
    PathSerializer,
    SiteSerializer,
    StoragePolicySerializer,
)
from ESSArch_Core.WorkflowEngine import get_workers

try:
    from pip._internal.operations.freeze import freeze as pip_freeze
except ImportError:  # pip < 10.0
    from pip.operations.freeze import freeze as pip_freeze


logger = logging.getLogger('essarch.configuration')


def get_database_info():
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


def get_elasticsearch_info(full):
    try:
        props = get_es_connection().info()
        if full:
            return props
        return {'version': props['version']}
    except ElasticsearchException:
        logger.exception("Could not connect to Elasticsearch.")
        return {
            'version': 'unknown',
            'error': 'Error connecting to Elasticsearch. Check the logs for more detail.'
        }


def get_redis_info(full=False):
    try:
        props = get_redis_connection().info()
        if full:
            props['version'] = props.pop('redis_version')
            return props
        return {'version': props['redis_version']}
    except RedisError:
        logger.exception("Could not connect to Redis.")
        return {
            'version': 'unknown',
            'error': 'Error connecting to Redis. Check the logs for more detail.'
        }


def get_rabbitmq_info(full=False):
    try:
        props = current_app.connection().connection.server_properties
        if full:
            return props
        return {'version': props['version']}
    except OSError:
        logger.exception("Could not connect to RabbitMQ.")
        return {
            'version': 'unknown',
            'error': 'Error connecting to RabbitMQ. Check the logs for more detail.'
        }


class SysInfoView(APIView):
    """
    API endpoint that allows system info to be viewed
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        full = string_to_bool(request.query_params.get('full', 'false'))
        context = {}

        # Flags in settings: Their expected  and actual values.
        SETTINGS_FLAGS = [
            ('DEBUG', False),
            ('LANGUAGE_CODE', None),
            ('TIME_ZONE', None),
        ]

        context['python'] = '.'.join(str(x) for x in sys.version_info[:3])
        context['platform'] = {
            'os': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'mac_version': platform.mac_ver(),
            'win_version': platform.win32_ver(),
            'linux_dist': distro.linux_distribution(),
        }
        context['hostname'] = socket.gethostname()
        context['version'] = get_versions()
        context['time_checked'] = timezone.now()
        context['database'] = get_database_info()

        context['elasticsearch'] = get_elasticsearch_info(full)
        context['redis'] = get_redis_info(full)
        context['rabbitmq'] = get_rabbitmq_info(full)
        context['workers'] = get_workers(context['rabbitmq'])
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
    filterset_class = EventTypeFilter
    filter_backends = (
        filters.OrderingFilter, DjangoFilterBackend, SearchFilter,
    )
    search_fields = ('eventDetail',)


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


class StoragePolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archive policies to be viewed or edited.
    """
    queryset = StoragePolicy.objects.all()
    serializer_class = StoragePolicySerializer
    filter_backends = (SearchFilter,)
    search_fields = ('policy_id', 'policy_name')


class SiteView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        site = Site.objects.first()
        if site is None:
            return Response()

        serializer = SiteSerializer(instance=site)
        return Response(serializer.data)
