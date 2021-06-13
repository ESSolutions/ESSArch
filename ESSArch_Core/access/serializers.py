from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ESSArch_Core.access.models import (
    AccessAid,
    AccessAidType
)
from ESSArch_Core.api.validators import StartDateEndDateValidator
from ESSArch_Core.auth.models import GroupGenericObjects
from ESSArch_Core.auth.serializers import GroupSerializer


class AccessAidTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessAidType
        fields = ('id', 'name')


class AccessAidSerializer(serializers.ModelSerializer):
    type = AccessAidTypeSerializer(read_only=True)
    organization = serializers.SerializerMethodField()

    def get_organization(self, obj):
        try:
            serializer = GroupSerializer(instance=obj.get_organization().group)
            return serializer.data
        except GroupGenericObjects.DoesNotExist:
            return None

    class Meta:
        model = AccessAid
        fields = (
            'id',
            'name',
            'type',
            'description',
            'start_date',
            'end_date',
            'security_level',
            'link',
            'organization',
        )


class AccessAidWriteSerializer(AccessAidSerializer):
    type = serializers.PrimaryKeyRelatedField(queryset=AccessAidType.objects.all())

    @transaction.atomic
    def create(self, validated_data):
        access_aid = super().create(validated_data)
        user = self.context['request'].user

        organization = user.user_profile.current_organization
        organization.assign_object(access_aid)
        organization.add_object(access_aid)
        #access_aid = AccessAid.objects.create(**validated_data)

        #org = self.context['request'].user.user_profile.current_organization
        #org.add_object(access_aid)

        return access_aid


    class Meta(AccessAidSerializer.Meta):
        fields = ('name', 'type', 'description', 'start_date', 'end_date', 'security_level')

        validators = [
            StartDateEndDateValidator(
                start_date='start_date',
                end_date='end_date',
            )
        ]
