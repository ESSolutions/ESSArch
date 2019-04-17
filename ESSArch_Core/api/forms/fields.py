from django import forms

from ESSArch_Core.api.forms.widgets import MultipleTextWidget


class MultipleTextField(forms.Field):
    widget = MultipleTextWidget
