"""Abstract class for serializing flows."""
from abc import ABC, abstractmethod

from pyof.v0x04.controller2switch.flow_mod import FlowModCommand as CommonFlowModCommand


class FlowSerializer(ABC):
    """Code 1.3 flow serialization.

    For a FlowMod dictionary, create a FlowMod message and, for a FlowStats,
    create a dictionary.
    """

    # These values are for version 1.3
    OFPFC_ADD = CommonFlowModCommand.OFPFC_ADD
    OFPFC_DELETE = CommonFlowModCommand.OFPFC_DELETE

    def __init__(self):
        """Initialize common attributes of version 1.3."""
        self.flow_attributes = set(
            ("priority", "idle_timeout", "hard_timeout", "cookie")
        )

    @abstractmethod
    def to_dict(self, flow_stats):
        """Return a serialized dictionary for a FlowStats message."""
