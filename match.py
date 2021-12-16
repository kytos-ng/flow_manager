"""Switch match."""

from napps.kytos.flow_manager.v0x01.match import match10_no_strict
from napps.kytos.flow_manager.v0x04.match import match13_no_strict, match13_strict


def match_flow(flow_to_install, version, stored_flow_dict):
    """Check that the flow fields match.

    It has support for (OF 1.0) and (OF 1.3) flows.
    If fields match, return the flow, otherwise return False.
    Does not require that all fields match.
    """
    if version == 0x01:
        return match10_no_strict(flow_to_install, stored_flow_dict)
    elif version == 0x04:
        return match13_no_strict(flow_to_install, stored_flow_dict)
    raise NotImplementedError(f"Unsupported OpenFlow version {version}")


def match_strict_flow(flow_to_install, version, stored_flow_dict) -> None:
    """Match the flow strictly.

    It has support for only for (OF 1.3) flows.
    If all fields match, return the flow, otherwise return False.
    """
    if version != 0x04:
        raise NotImplementedError(f"Unsupported OpenFlow version {version}")
    return match13_strict(flow_to_install, stored_flow_dict)
