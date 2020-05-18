from ESSArch_Core.exceptions import ESSArchException


class ConversionError(ESSArchException):
    pass


class CollectionError(ESSArchException):
    pass


class TransformationError(ESSArchException):
    pass


class ValidationError(ESSArchException):
    pass
