import click


class BaseTransformer:
    def __init__(self, ip=None, user=None):
        self.ip = ip
        self.user = user

    @classmethod
    def transform(cls, path):
        raise NotImplementedError('Subclasses of BaseTransformer must provide a transform() method')

    @staticmethod
    @click.command()
    def cli(path):
        raise NotImplementedError('Subclasses of BaseTransformer must provide a cli() method')
