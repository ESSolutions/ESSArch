from rest_framework import serializers

from ESSArch_Core.tags.documents import VersionedDocType
from ESSArch_Core.tags.models import Tag

class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('link_id', 'version_start_date', 'version_end_date',
                  'name', 'type', 'parent',)

class TagSerializer(serializers.ModelSerializer):
    _id = serializers.UUIDField(source='id')
    _index = serializers.CharField(source='index')
    is_leaf_node = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    _source = serializers.SerializerMethodField()

    def get_is_leaf_node(self, obj):
        return obj.is_leaf_node()

    def get_parent(self, obj):
        if obj.parent is None:
            return None

        return {
            'id': str(obj.parent.pk),
            'index': obj.parent.index
        }

    def get__source(self, obj):
        doc = VersionedDocType.get(index=obj.index, id=str(obj.pk))
        return doc.to_dict()

    class Meta:
        model = Tag
        fields = ('_id', '_index', 'link_id', 'current_version',
                  'create_date', 'version_start_date', 'version_end_date',
                  'name', 'type', 'is_leaf_node', 'parent', '_source')


class TagSerializerWithVersions(TagSerializer):
    versions = serializers.SerializerMethodField()

    def get_versions(self, obj):
        tags = obj.get_versions().order_by('create_date')
        return TagSerializer(tags, many=True).data

    class Meta(TagSerializer.Meta):
        fields = TagSerializer.Meta.fields + ('versions',)
