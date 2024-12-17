import click


class BaseTransformer:
    file_transformer = True  # Does the validator operate on single files or entire directories?

    def __init__(self, context=None, include=None, exclude=None, options=None,
                 data=None, required=True, task=None, ip=None, responsible=None,
                 stylesheet=None):
        """
        Initializes for transform of one or more files
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
        self.stylesheet = stylesheet

    @classmethod
    def transform(cls, path):
        raise NotImplementedError('Subclasses of BaseTransformer must provide a transform() method')

    @staticmethod
    @click.command()
    def cli(path):
        raise NotImplementedError('Subclasses of BaseTransformer must provide a cli() method')
