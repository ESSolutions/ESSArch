from rest_framework import status
from rest_framework.exceptions import APIException


class ESSArchException(Exception):
    """
    Base class for all exceptions defined in this package
    """


class EncryptedFileNotAllowed(ESSArchException):
    pass


class FileFormatNotAllowed(ESSArchException):
    pass


class ValidationError(ESSArchException):
    def __init__(self, message, errors=None):
        super().__init__(message)

        if errors is None:
            errors = []

        self.errors = errors


class Locked(APIException, ESSArchException):
    status_code = status.HTTP_423_LOCKED
    default_detail = 'The resource that is being accessed is locked'
    default_code = 'locked'


class Conflict(APIException, ESSArchException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The request could not be completed due to a conflict with the target resource'
    default_code = 'conflict'


class NoFileChunksFound(ESSArchException):
    pass
