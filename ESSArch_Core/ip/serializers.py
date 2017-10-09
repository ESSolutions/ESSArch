from _version import get_versions

from rest_framework import serializers

from ESSArch_Core.auth.fields import CurrentUsernameDefault
from ESSArch_Core.configuration.models import EventType
from ESSArch_Core.ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    EventIP,
)

VERSION = get_versions()['version']

class ArchivalInstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalInstitution
        fields = ('url', 'id', 'name',)


class ArchivistOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivistOrganization
        fields = ('url', 'id', 'name',)


class ArchivalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalType
        fields = ('url', 'id', 'name',)


class ArchivalLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalLocation
        fields = ('url', 'id', 'name',)

class EventIPSerializer(serializers.HyperlinkedModelSerializer):
    linkingAgentIdentifierValue = serializers.CharField(read_only=True, default=CurrentUsernameDefault())
    information_package = serializers.CharField(required=False, source='linkingObjectIdentifierValue')
    eventType = serializers.PrimaryKeyRelatedField(queryset=EventType.objects.all())
    eventDetail = serializers.SlugRelatedField(slug_field='eventDetail', source='eventType', read_only=True)

    class Meta:
        model = EventIP
        fields = (
                'url', 'id', 'eventType', 'eventDateTime', 'eventDetail',
                'eventVersion', 'eventOutcome',
                'eventOutcomeDetailNote', 'linkingAgentIdentifierValue',
                'information_package',
        )
        extra_kwargs = {
            'eventVersion': {
                'default': VERSION
            }
        }
