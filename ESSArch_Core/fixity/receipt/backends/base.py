class BaseReceiptBackend:
    def create(self, template, destination, outcome, short_message, message, date, ip=None, task=None, **kwargs):
        raise NotImplementedError('subclasses of BaseReceiptBackend must provide a create() method')
