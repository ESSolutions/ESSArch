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

from rest_framework import serializers

from ESSArch_Core.configuration.models import (
    Agent,
    ArchivePolicy,
    EventType,
    Parameter,
    Path,
)


class EventTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = EventType
        fields = ('url', 'eventType', 'eventDetail',)


class AgentSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Agent
        fields = '__all__'


class ParameterSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Parameter
        fields = '__all__'


class PathSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Path
        fields = '__all__'


class ArchivePolicySerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ArchivePolicy
        fields = '__all__'
