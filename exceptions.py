"""Exceptions raised by this NApp."""


class InvalidCommandError(Exception):
    """Command has an invalid value."""


class SwitchNotConnectedError(Exception):
    """Exception raised when a switch's connection isn't connected."""

    def __init__(self, message, flow=None):
        """Init of SwitchNotConnectedError."""
        self.message = message
        self.flow = flow
        super().__init__(message)
