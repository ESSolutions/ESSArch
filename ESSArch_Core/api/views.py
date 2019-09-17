from django.db.models import Case, IntegerField, Value, When
from django_filters.rest_framework import DjangoFilterBackend
from languages_plus.models import Language
from rest_framework import viewsets

from ESSArch_Core.api.filters import SearchFilter
from ESSArch_Core.api.serializers import LanguageSerializer
from ESSArch_Core.auth.permissions import ActionPermissions


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    permission_classes = (ActionPermissions,)
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    search_fields = ('name_en',)

    def get_queryset(self):
        user_lang = self.request.user.user_profile.language

        return Language.objects.all().annotate(
            default_order=Case(
                When(iso_639_1=user_lang, then=Value(1)),
                When(iso_639_1='en', then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('default_order')
