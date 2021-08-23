from django.db import transaction
from rest_framework import serializers

from ESSArch_Core.access.models import AccessAid, AccessAidType
from ESSArch_Core.api.validators import StartDateEndDateValidator
from ESSArch_Core.auth.models import GroupGenericObjects
from ESSArch_Core.auth.serializers import GroupSerializer
from ESSArch_Core.tags.models import StructureUnit


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

        return access_aid

    class Meta(AccessAidSerializer.Meta):
        fields = ('name', 'type', 'description', 'start_date', 'end_date', 'security_level', 'link')

        validators = [
            StartDateEndDateValidator(
                start_date='start_date',
                end_date='end_date',
            )
        ]


class AccessAidEditNodesSerializer(serializers.Serializer):
    structure_units = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(
            queryset=StructureUnit.objects.filter(structure__is_template=False),
        )
    )
