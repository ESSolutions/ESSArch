class BaseTransformer(object):
    def __init__(self, ip=None, options=None, data=None):
        self.ip = ip
        self.options = options or {}
        self.data = data or {}

    def transform(self, path):
        raise NotImplementedError('subclasses of BaseTransformer must provide a transform() method')
