from itertools import takewhile

from django import forms
from django_filters.fields import RangeField

from ESSArch_Core.api.forms.widgets import MultipleTextWidget


class MultipleTextField(forms.Field):
    widget = MultipleTextWidget


class CharSuffixRangeField(RangeField):
    def __init__(self, fields=None, *args, **kwargs):
        if fields is None:
            fields = (
                forms.CharField(),
                forms.CharField())
        super().__init__(fields, *args, **kwargs)

    @staticmethod
    def _get_suffix(value):
        suffix = ''.join(list(takewhile(str.isdigit, value[::-1])))[::-1]
        pos = len(value) - len(suffix)
        return suffix, pos

    def clean(self, value):
        from django.core.exceptions import ValidationError
        value = super().clean(value)

        if value is None:
            return None

        start = value.start
        stop = value.stop

        if len(start) != len(stop):
            raise ValidationError('min and max must be of same length')

        if not start[-1].isdigit() or not stop[-1].isdigit():
            raise ValidationError('min and max must end with a number')

        start_suffix, start_suffix_pos = self._get_suffix(start)
        stop_suffix, stop_suffix_pos = self._get_suffix(stop)

        start_prefix = start[:start_suffix_pos]
        stop_prefix = stop[:stop_suffix_pos]

        if start_suffix_pos != stop_suffix_pos or \
           start_prefix != stop_prefix:

            raise ValidationError('Format of min and max does not match')

        return (
            (start, start_suffix, start_suffix_pos),
            (stop, stop_suffix, stop_suffix_pos),
        )
