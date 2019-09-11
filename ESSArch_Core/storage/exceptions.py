from ESSArch_Core.exceptions import ESSArchException


class RobotException(ESSArchException):
    pass


class RobotMountException(RobotException):
    pass


class RobotMountTimeoutException(RobotMountException):
    pass


class RobotUnmountException(RobotException):
    pass


class MTInvalidOperationOrDeviceNameException(ESSArchException):
    pass


class MTFailedOperationException(ESSArchException):
    pass


class StorageMediumFull(ESSArchException):
    pass


class TapeDriveLockedError(ESSArchException):
    """The tape drive is locked"""
    pass


class TapeMountedAndLockedByOtherError(ESSArchException):
    """The tape is mounted and locked by another process"""
    pass


class TapeMountedError(ESSArchException):
    """The tape is already mounted"""
    pass


class TapeUnmountedError(ESSArchException):
    """The tape is already unmounted"""
    pass
