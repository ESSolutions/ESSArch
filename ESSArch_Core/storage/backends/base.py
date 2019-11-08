from contextlib import contextmanager


class BaseStorageBackend:
    @contextmanager
    def open(self, storage_object, file, *args, **kwargs):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide an open() method')

    def prepare_for_read(self, storage_medium):
        """Called before reading from a storage medium"""
        pass

    def read(self, storage_object, dst, extract=False, include_xml=True, block_size=None):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide an read() method')

    def prepare_for_write(self, storage_medium):
        """Called before writing to a storage medium"""
        pass

    def write(self, src, ip, storage_method, storage_medium, block_size=None):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide an write() method')

    def delete(self, storage_object):
        raise NotImplementedError('subclasses of BaseStorageBackend must provide a delete() method')

    @classmethod
    def post_mark_as_full(cls, storage_medium):
        """Called after a medium has been successfully marked as full"""
        pass
