from ESSArch_Core.exceptions import ESSArchException


class InvalidFormat(ESSArchException):
    pass


class InvalidInputFormat(InvalidFormat):
    pass


class InvalidOutputFormat(InvalidFormat):
    pass
