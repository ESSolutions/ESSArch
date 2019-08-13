from collections import OrderedDict

from django.utils.encoding import force_text
from django_filters.utils import label_for_filter
from rest_framework.metadata import SimpleMetadata
from rest_framework.relations import ManyRelatedField, RelatedField

from ESSArch_Core.fixity.transformation import AVAILABLE_TRANSFORMERS
from ESSArch_Core.WorkflowEngine.polling import AVAILABLE_POLLERS


class CustomMetadata(SimpleMetadata):

    def determine_metadata(self, request, view):
        metadata = super().determine_metadata(request, view)

        metadata['transformers'] = AVAILABLE_TRANSFORMERS.keys()
        metadata['workflow_pollers'] = AVAILABLE_POLLERS.keys()

        filters = OrderedDict()
        if not getattr(view, 'filterset_class', None):
            # This route has no filter
            return metadata

        model = view.filterset_class.Meta.model
        for filter_name, filter_type in view.filterset_class.base_filters.items():
            filter_parts = filter_name.split('__')
            filter_name = filter_parts[0]
            attrs = OrderedDict()

            # Type
            attrs['type'] = filter_type.__class__.__name__

            # Lookup fields
            if len(filter_parts) > 1:
                # Has a lookup type (__gt, __lt, etc.)
                lookup_type = filter_parts[1]
                if filters.get(filter_name) is not None:
                    # We've done a filter with this name previously, just
                    # append the value.
                    attrs['lookup_types'] = filters[filter_name]['lookup_types']
                    attrs['lookup_types'].append(lookup_type)
                else:
                    attrs['lookup_types'] = [lookup_type]
            else:
                attrs['lookup_types'] = ['exact']

            # Do choices
            choices = filter_type.extra.get('choices', False)
            if choices:
                attrs['choices'] = [
                    {
                        'value': choice_value,
                        'display_name': force_text(choice_name, strings_only=True)
                    }
                    for choice_value, choice_name in choices
                ]

            # Do queryset
            queryset = filter_type.extra.get('queryset', False)
            to_field = filter_type.extra.get('to_field_name', 'pk')
            if queryset:
                if callable(queryset):
                    queryset = queryset(request)

                attrs['choices'] = [
                    {
                        'value': force_text(getattr(choice, to_field), strings_only=True),
                        'display_name': force_text(choice, strings_only=True)
                    }
                    for choice in queryset
                ]

            label = filter_type.label
            if label is None:
                if model is not None:
                    label = label_for_filter(
                        model,
                        filter_type.field_name,
                        filter_type.lookup_expr,
                        filter_type.exclude
                    )
                else:
                    label = filter_name.replace('_', ' ').title()

            attrs['label'] = label

            # Wrap up.
            filters[filter_name] = attrs

        metadata['filters'] = filters

        if getattr(view, 'ordering_fields', None):
            metadata['ordering'] = view.ordering_fields

        if getattr(view, 'search_fields', None) and len(view.search_fields) > 1:
            metadata['search'] = True

        return metadata
