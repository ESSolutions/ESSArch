class BaseReceiptBackend(object):
    def create(self, template, destination, outcome, short_message, message, date, ip=None, task=None):
        raise NotImplementedError('subclasses of BaseReceiptBackend must provide a create() method')
