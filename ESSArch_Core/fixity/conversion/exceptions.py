from ESSArch_Core.exceptions import ESSArchException


class UnknownConverter(ESSArchException):
    pass


class InvalidFormat(ESSArchException):
    pass


class InvalidInputFormat(InvalidFormat):
    pass


class InvalidOutputFormat(InvalidFormat):
    pass
