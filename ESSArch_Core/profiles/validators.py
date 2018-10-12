from django.core.exceptions import ValidationError
from django.core.validators import validate_email, URLValidator

from ESSArch_Core.util import validate_remote_url


def validate_template(template, data):
    for field in template:
        key = field.get('key')
        to = field.get('templateOptions', {})

        if to.get('required') and len(data.get(key, '')) == 0:
            if 'defaultValue' not in field:
                raise ValidationError('Required field "%s" can\'t be empty' % key)
            else:
                data[key] = field['defaultValue']

        if to.get('type') == 'email' and data.get(key):
            validate_email(data.get(key))

        elif to.get('type') == 'url' and 'remote' in to.keys() and data.get(key):
            validate_remote_url(data.get(key))

        elif to.get('type') == 'url' and data.get(key):
            validate_url = URLValidator()
            validate_url(data.get(key))
