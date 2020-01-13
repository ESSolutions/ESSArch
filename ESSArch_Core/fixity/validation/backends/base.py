import click


class BaseValidator:
    file_validator = True  # Does the validator operate on single files or entire directories?

    def __init__(self, context=None, include=None, exclude=None, options=None,
                 data=None, required=True, task=None, ip=None, responsible=None):
        """
        Initializes for validation of one or more files
        """
        self.context = context
        self.include = include or []
        self.exclude = exclude or []
        self.options = options or {}
        self.data = data or {}
        self.required = required
        self.task = task
        self.ip = ip
        self.responsible = responsible

    def validate(self, filepath, expected=None):
        raise NotImplementedError('subclasses of BaseValidator must provide a validate() method')

    @staticmethod
    @click.command()
    def cli(path):
        raise NotImplementedError('Subclasses of BaseValidator must provide a cli() method')
