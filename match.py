"""Switch match."""

from napps.kytos.flow_manager.v0x04.match import match13_no_strict


def match_flow(flow_to_install, version, stored_flow_dict):
    """Check that the flow fields match.

    It has support (OF 1.3) flows.
    If fields match, return the flow, otherwise return False.
    Does not require that all fields match.
    """
    if version == 0x04:
        return match13_no_strict(flow_to_install, stored_flow_dict)
    raise NotImplementedError(f"Unsupported OpenFlow version {version}")
