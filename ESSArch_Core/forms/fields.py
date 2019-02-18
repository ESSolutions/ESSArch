from django import forms
from django_filters.fields import IsoDateTimeField, RangeField
from django_filters.widgets import DateRangeWidget

from ESSArch_Core.forms.widgets import MultipleTextWidget


class IsoDateTimeRangeField(RangeField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (IsoDateTimeField(), IsoDateTimeField())
        super().__init__(fields, *args, **kwargs)


class MultipleTextField(forms.Field):
    widget = MultipleTextWidget
