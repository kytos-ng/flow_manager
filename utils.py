"""kytos/flow_manager utils."""

from pyof.foundation.base import UBIntBase
from pyof.v0x04.controller2switch.flow_mod import FlowModCommand

from kytos.core import log

from .exceptions import InvalidCommandError


def build_flow_mod_from_command(flow, command):
    """Build a FlowMod serialized given a command."""
    if command == "delete":
        flow_mod = flow.as_of_delete_flow_mod()
    elif command == "delete_strict":
        flow_mod = flow.as_of_strict_delete_flow_mod()
    elif command == "add":
        flow_mod = flow.as_of_add_flow_mod()
    else:
        raise InvalidCommandError
    return flow_mod


def build_command_from_flow_mod(flow_mod) -> str:
    """Build a command str given a FlowMod."""
    commands = {
        FlowModCommand.OFPFC_ADD.value: "add",
        FlowModCommand.OFPFC_DELETE.value: "delete",
        FlowModCommand.OFPFC_DELETE_STRICT.value: "delete_strict",
    }
    try:
        return commands[flow_mod.command.value]
    except KeyError:
        return str(flow_mod.command.value)


def is_ignored(field, ignored_range):
    """Check that the flow field is in the range of ignored flows.

    Returns True, if the field is in the range of ignored flows,
    otherwise it returns False.
    """
    for i in ignored_range:
        if isinstance(i, tuple):
            start_range, end_range = i
            if start_range <= field <= end_range:
                return True
        if isinstance(i, int):
            if field == i:
                return True
    return False


def cast_fields(flow_dict):
    """Make casting the match fields from UBInt() to native int ."""
    match = flow_dict["match"]
    for field, value in match.items():
        if isinstance(value, UBIntBase):
            match[field] = int(value)
    flow_dict["match"] = match
    return flow_dict


def _validate_range(values):
    """Check that the range of flows ignored by the consistency is valid."""
    if len(values) != 2:
        msg = f"The tuple must have 2 items, not {len(values)}"
        raise ValueError(msg)
    first, second = values
    if not isinstance(first, int) or not isinstance(second, int):
        msg = f"Expected a tuple of integers, received {values}"
        raise TypeError(msg)
    if second < first:
        msg = f"The first value is bigger than the second: {values}"
        raise ValueError(msg)


def _valid_consistency_ignored(consistency_ignored_list):
    """Check the format of the list of ignored consistency flows.

    Check that the list of ignored flows in the consistency check
    is well formatted. Returns True, if the list is well
    formatted, otherwise return False.
    """
    msg = (
        "The list of ignored flows in the consistency check"
        "is not well formatted, it will be ignored: %s"
    )
    for consistency_ignored in consistency_ignored_list:
        if isinstance(consistency_ignored, tuple):
            try:
                _validate_range(consistency_ignored)
            except (TypeError, ValueError) as error:
                log.warn(msg, error)
                return False
        elif not isinstance(consistency_ignored, (int, tuple)):
            error_msg = (
                "The elements must be of class int or tuple"
                f" but they are: {type(consistency_ignored)}"
            )
            log.warn(msg, error_msg)
            return False
    return True


def get_min_wait_diff(datetime_t2, datetime_t1, min_wait):
    """Compute the min wait diff given two datetimes in secs, where t2 >= t1 in secs."""
    if (datetime_t2 <= datetime_t1) or min_wait <= 0:
        return 0
    datetime_diff = (datetime_t2 - datetime_t1).total_seconds()
    min_wait_diff = min_wait - datetime_diff
    if min_wait_diff <= 0:
        return 0
    return min_wait_diff
