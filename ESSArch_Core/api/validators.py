from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError


class StartDateEndDateValidator:
    message = _('End date must occur after start date')

    def __init__(self, start_date, end_date, message=None):
        self.start_date = start_date
        self.end_date = end_date
        self.serializer_field = None
        self.message = message or self.message

    def __call__(self, attrs):
        start_date = attrs.get(self.start_date)
        end_date = attrs.get(self.end_date)

        if start_date and end_date and start_date > end_date:
            raise ValidationError(self.message)
