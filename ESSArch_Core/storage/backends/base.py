from contextlib import contextmanager

class BaseStorageBackend(object):
    @contextmanager
    def open(self, storage_object, file, *args, **kwargs):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide an open() method')

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=None):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide an read() method')

    def write(self, src, ip, storage_method, storage_medium, block_size=None):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide an write() method')

    def delete(self, storage_object):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide a delete() method')
