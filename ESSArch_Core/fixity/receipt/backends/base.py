from ESSArch_Core.profiles.utils import fill_specification_data


class BaseReceiptBackend(object):
    def __init__(self, ip):
        self.ip = ip
        self.data = fill_specification_data(ip=self.ip)

    def create(self, template, destination, outcome, short_message, message, date, ip=None, task=None):
        raise NotImplementedError('subclasses of BaseReceiptBackend must provide a create() method')
