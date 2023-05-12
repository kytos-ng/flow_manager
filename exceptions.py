"""Exceptions raised by this NApp."""


class InvalidCommandError(Exception):
    """Command has an invalid value."""


class FlowSerializerError(Exception):
    """FlowSerializerError."""

    def __init__(self, message, flow_dict=None):
        """Constructor."""
        self.message = message
        self.flow_dict = flow_dict
        super().__init__(message)


class SwitchNotConnectedError(Exception):
    """Exception raised when a switch's connection isn't connected."""

    def __init__(self, message, flow=None):
        """Init of SwitchNotConnectedError."""
        self.message = message
        self.flow = flow
        super().__init__(message)
