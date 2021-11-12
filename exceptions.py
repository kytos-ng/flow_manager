"""Exceptions raised by this NApp."""


class InvalidCommandError(Exception):
    """Command has an invalid value."""


class SwitchNotConnectedError(Exception):
    """Exception raised when a switch's connection isn't connected."""
