import logging

import click
from wand.image import Image

from ESSArch_Core.fixity.conversion.backends.base import BaseConverter
from ESSArch_Core.fixity.conversion.exceptions import InvalidFormat


class ImageConverter(BaseConverter):
    logger = logging.getLogger('essarch.fixity.conversion.backends.image')

    input_formats = [
        'image/bmp',
        'image/cals',
        'image/x-cals',
        'image/jpeg',
        'image/png',
    ]

    output_formats = [
        'image/bmp',
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

    @classmethod
    def convert(cls, input_file, output_file, in_fmt=None, out_fmt=None):
        with Image(filename=input_file) as in_img:
            out_fmt = cls.format_from_mimetype(out_fmt)
            in_img.format = out_fmt
            in_img.save(filename=output_file)

    @staticmethod
    @click.command()
    @click.argument('input_file', metavar='INPUT', type=click.Path(exists=True))
    @click.argument('output_file', metavar='OUTPUT', type=click.Path())
    @click.option('--in-fmt', 'in_fmt', type=click.Choice(input_formats), help="Format of the input file")
    @click.option('--out-fmt', 'out_fmt', type=click.Choice(output_formats), help="Format of the output file")
    def cli(input_file, output_file, in_fmt, out_fmt):
        """Convert images using ImageMagick"""
        return ImageConverter.convert(input_file, output_file, in_fmt, out_fmt)
