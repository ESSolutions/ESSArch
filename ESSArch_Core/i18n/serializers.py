from rest_framework import serializers, validators

from ESSArch_Core.i18n.models import Language


class LanguageSerializer(serializers.ModelSerializer):
    id = serializers.CharField(
        source='iso_639_1', max_length=2,
        validators=[validators.UniqueValidator(queryset=Language.objects.all())],
    )

    class Meta:
        model = Language
        fields = ('id', 'name_en',)
