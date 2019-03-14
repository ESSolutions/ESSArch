import logging

from wand.image import Image

from ESSArch_Core.fixity.conversion.backends.base import BaseConverter
from ESSArch_Core.fixity.conversion.exceptions import InvalidFormat

logger = logging.getLogger('essarch.fixity.conversion.backends.image')


class ImageConverter(BaseConverter):
    input_formats = [
        'image/cals',
        'image/x-cals',
        'image/jpeg',
        'image/png',
    ]

    output_formats = [
        'image/cals',
        'image/x-cals',
        'image/jpeg',
        'image/png',
    ]

    mimetype_formats = {
        'image/cals': 'CALS',
        'image/x-cals': 'CALS',
        'image/jpeg': 'JPEG',
        'image/png': 'PNG',
    }

    @classmethod
    def format_from_mimetype(cls, fmt):
        try:
            return cls.mimetype_formats[fmt]
        except KeyError:
            raise InvalidFormat('Mimetype "{}" not found'.format(fmt))

    def convert(self, input_file, output_file, in_fmt=None, out_fmt=None, **kwargs):
        with Image(filename=input_file) as in_img:
            out_fmt = self.format_from_mimetype(out_fmt)
            in_img.format = out_fmt
            in_img.save(filename=output_file)
