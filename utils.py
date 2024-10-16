"""kytos/flow_manager utils."""

from collections.abc import Callable

from pyof.foundation.base import UBIntBase
from pyof.v0x04.controller2switch.flow_mod import FlowModCommand
from typing import Union
from kytos.core import log
from typing import Union
from .exceptions import InvalidCommandError


def build_cookie_range_tuple(cookie: int, cookie_mask: int) -> tuple[int, int]:
    """Build a cookie range tuple.

    cookie_mask 1's mean exact match and 0's mean don't care. To compute the
    maximum cookie value, you get the mask binary complement up to 8 bytes and
    logically add to the initial value of the cookie.
    """
    cookie_high = cookie | (~cookie_mask & 0xFFFFFFFFFFFFFFFF)
    return cookie & cookie_mask, cookie_high


def map_cookie_list_as_tuples(cookies: list[int]) -> list[tuple[int, int]]:
    """Map cookie list as tuples."""
    if len(cookies) % 2 == 1:
        raise ValueError(f"Expected cookies length to be even, got length {cookies}")
    stack = []
    for i in range(1, len(cookies), 2):
        stack.append((cookies[i - 1], cookies[i]))
    return stack


def merge_cookie_ranges(cookie_ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlaping cookie ranges to simplify DB "$or" operator query complexity."""
    if len(cookie_ranges) <= 1:
        return cookie_ranges
    ranges = sorted(cookie_ranges, key=lambda x: (x[0], x[1]))
    stack = [ranges[0]]
    for i in range(1, len(ranges)):
        range_low, range_high = ranges[i]
        stack_low, stack_high = stack[-1]
        if range_low <= stack_high:
            stack.pop()
            stack.append((min(stack_low, range_low), max(stack_high, range_high)))
        else:
            stack.append((range_low, range_high))
    return stack


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
                log.warning(msg, error)
                return False
        elif not isinstance(consistency_ignored, (int, tuple)):
            error_msg = (
                "The elements must be of class int or tuple"
                f" but they are: {type(consistency_ignored)}"
            )
            log.warning(msg, error_msg)
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


def validate_cookies_and_masks(flows: list[dict], command: str) -> None:
    """Validate cookies and masks."""
    validators = {"add": validate_cookies_add, "delete": validate_cookies_del}
    if command in validators:
        validators[command](flows)


def validate_cookies_add(flows: list[dict]) -> None:
    """Validate cookies add."""
    for flow in flows:
        if "cookie_mask" in flow:
            raise ValueError(
                f"cookie_mask shouldn't be set when adding flows. flow: {flow}"
            )


def validate_cookies_del(flows: list[dict]) -> None:
    """Validate cookies del."""
    for flow in flows:
        has_cookie, has_mask = "cookie" in flow, "cookie_mask" in flow

        if not has_cookie and not has_mask:
            continue
        if has_cookie and not has_mask:
            raise ValueError(
                "cookie is set, cookie_mask should be set too "
                f"when deleting flows. flow: {flow}"
            )
        if not has_cookie and has_mask:
            raise ValueError(
                "cookie_mask is set, cookie should be set too"
                f"when deleting flows. flow: {flow}"
            )

def flows_to_log(
    logger_fun: Callable,
    message: str,
    switches: list[str],
    flows_dict: Union[
        dict[str, dict[str, list]], # by_switch=True
        dict[str, list]             # by_switch=False
    ],
    by_switch=False
):
    """Log the information of installing or deleting flows. The logs will
     show the quantity of flows being modified in each switch or all
     existent switches.
     If flows are sent by switch, each switch will log the flows modified."""
    log_str = "Batched of flows received: "
    count_flows = 0
    for switch in switches:
        if not by_switch:
            flows_n = len(flows_dict['flows'])
            log_str = log_str + f" switches:{switches}, flows_by_switch:{flows_n}, "
            count_flows = flows_n*len(switches)
            _flows_to_log(logger_fun, message, switches, flows_dict['flows'])
            break
        
        flows_n = len(flows_dict[switch]['flows'])
        log_str = log_str + f"{{switch: {switch}, flows_lenght: {flows_n}}}, "
        count_flows += flows_n
        _flows_to_log(logger_fun, message, [switch], flows_dict[switch]['flows'])
    logger_fun(f"{log_str} total_flows_length: {count_flows}")

def _flows_to_log(
    logger_fun: Callable,
    message: str,
    switches: list[str],
    flow_list: list,
):
    """Logs the flows within a limit."""
    maximun = 200
    i, j = 0, maximun
    while flow_list[i:j]:
        logger_fun(
            f"{message}{switches}, flows[{i}, {(j if j < len(flow_list) else len(flow_list))}]:"
            f" {flow_list[i:j]}"
        )
        i, j = j, j + maximun