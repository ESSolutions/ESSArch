class BaseTransformer(object):
    def __init__(self, ip=None, user=None):
        self.ip = ip
        self.user = user

    def transform(self, path):
        raise NotImplementedError('subclasses of BaseTransformer must provide a transform() method')
