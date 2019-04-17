from django import forms


class MultipleTextWidget(forms.widgets.Widget):
    template_name = 'django/forms/widgets/text.html'

    def format_value(self, value):
        """Return selected values as a list."""
        if value is None:
            return []
        if not isinstance(value, (tuple, list)):
            value = [value]
        return [str(v) if v is not None else '' for v in value]

    def value_from_datadict(self, data, files, name):
        getter = data.get
        try:
            getter = data.getlist
        except AttributeError:
            pass
        return getter(name)
