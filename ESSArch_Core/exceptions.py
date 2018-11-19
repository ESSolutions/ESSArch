from rest_framework import status
from rest_framework.exceptions import APIException


class FileFormatNotAllowed(Exception):
    pass


class ValidationError(Exception):
    def __init__(self, message):
        super(ValidationError, self).__init__(message)
        self.message = message


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'The request could not be completed due to a conflict with the target resource'
    default_code = 'conflict'


class NoFileChunksFound(Exception):
    pass
