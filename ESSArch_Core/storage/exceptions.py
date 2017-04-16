class RobotException(Exception):
    pass


class RobotMountException(RobotException):
    pass


class RobotMountTimeoutException(RobotMountException):
    pass


class RobotUnmountException(RobotException):
    pass


class MTInvalidOperationOrDeviceNameException(Exception):
    pass


class MTFailedOperationException(Exception):
    pass
