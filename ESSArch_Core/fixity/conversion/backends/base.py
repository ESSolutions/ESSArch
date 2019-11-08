import click

from ..exceptions import InvalidInputFormat, InvalidOutputFormat


class BaseConverter:
    input_formats = []
    output_formats = []

    def __init__(self, ip=None, user=None):
        self.ip = ip
        self.user = user

    @classmethod
    def validate_input_format(cls, fmt):
        if fmt not in cls.input_formats:
            raise InvalidInputFormat('{} is not a valid input format for {}'.format(fmt, cls.__name__))

    @classmethod
    def validate_output_format(cls, fmt):
        if fmt not in cls.output_formats:
            raise InvalidOutputFormat('{} is not a valid output format for {}'.format(fmt, cls.__name__))

    @classmethod
    def validate_formats(cls, in_fmt=None, out_fmt=None):
        if in_fmt is not None:
            cls.validate_input_format(in_fmt)

        if out_fmt is not None:
            cls.validate_output_format(out_fmt)

    @classmethod
    def convert(cls, input_file, output_file, in_fmt=None, out_fmt=None):
        raise NotImplementedError('Subclasses of BaseConverter must provide a convert() method')

    def _convert(self, input_file, output_file, in_fmt=None, out_fmt=None):
        self.validate_formats(in_fmt=in_fmt, out_fmt=out_fmt)
        msg_context = {
            'input': input_file,
            'output': output_file,
            'in_fmt': '({})'.format(in_fmt) if in_fmt else '',
            'out_fmt': '({})'.format(out_fmt) if out_fmt else '',
            'conv': self.__class__.__name__,
        }

        msg = 'Converting {input}{in_fmt} to {output}{out_fmt} using {conv}'.format(**msg_context),
        self.logger.debug(msg)

        self.convert(input_file, output_file, in_fmt=in_fmt, out_fmt=out_fmt)

        msg = 'Converted {input}{in_fmt} to {output}{out_fmt} using {conv}'.format(**msg_context),
        self.logger.info(msg)

    @staticmethod
    @click.command()
    def cli(input_file, output_file, in_fmt, out_fmt):
        raise NotImplementedError('Subclasses of BaseConverter must provide a cli() method')
