"""Module to test the utils module."""
from datetime import timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest
from napps.kytos.flow_manager.exceptions import InvalidCommandError
from napps.kytos.flow_manager.utils import (
    _valid_consistency_ignored,
    _validate_range,
    build_command_from_flow_mod,
    build_cookie_range_tuple,
    build_flow_mod_from_command,
    get_min_wait_diff,
    map_cookie_list_as_tuples,
    merge_cookie_ranges,
    validate_cookies_add,
    validate_cookies_del,
    flows_to_log_info,
)
from pyof.v0x04.controller2switch.flow_mod import FlowModCommand


@pytest.mark.parametrize(
    "value,expected",
    [
        (FlowModCommand.OFPFC_ADD.value, "add"),
        (FlowModCommand.OFPFC_DELETE.value, "delete"),
        (FlowModCommand.OFPFC_DELETE_STRICT.value, "delete_strict"),
        (FlowModCommand.OFPFC_MODIFY.value, str(FlowModCommand.OFPFC_MODIFY.value)),
    ],
)
def test_build_command_from_flow_mod(value, expected):
    """Test build_command_from_flow_mod."""
    mock = MagicMock()
    mock.command.value = value
    assert build_command_from_flow_mod(mock) == expected


def test_build_flow_mod_from_command_exc():
    """test build_flow_mod_from_command."""
    with pytest.raises(InvalidCommandError):
        build_flow_mod_from_command(MagicMock(), "invalid_command")


@pytest.mark.parametrize(
    "cookie,cookie_mask,expected",
    [
        (
            0x0000000000000000,
            0xFFFFFFFFFFFFFFFF,
            (0x0000000000000000, 0x0000000000000000),
        ),
        (
            0x0000000000000000,
            0x0000000000000000,
            (0x0000000000000000, 0xFFFFFFFFFFFFFFFF),
        ),
        (
            0xAA00000000000000,
            0xFFFFFFFFFFFFFFFF,
            (0xAA00000000000000, 0xAA00000000000000),
        ),
        (
            0xAA00000000000000,
            0xFF00000000000000,
            (0xAA00000000000000, 0xAAFFFFFFFFFFFFFF),
        ),
        (
            0xAA00000000000000,
            0x0000000000000000,
            (0x0000000000000000, 0xFFFFFFFFFFFFFFFF),
        ),
        (
            0x0000000000000064,
            0xFFFFFFFFFFFFFFFE,
            (0x0000000000000064, 0x0000000000000065),
        ),
        (
            0x0000000000000060,
            0xFFFFFFFFFFFFFFF0,
            (0x0000000000000060, 0x000000000000006F),
        ),
    ],
)
def test_build_cookie_range_tuple(cookie, cookie_mask, expected) -> None:
    """Test build_range_tuple."""
    assert build_cookie_range_tuple(cookie, cookie_mask) == expected


@pytest.mark.parametrize(
    "cookie_ranges,merged",
    [
        (
            [(0, 10), (0, 5), (10, 11), (13, 14), (12, 20)],
            [(0, 11), (12, 20)],
        ),
        (
            [(0, 10), (13, 14), (12, 20), (0, 5), (10, 11)],
            [(0, 11), (12, 20)],
        ),
        (
            [(0, 10), (0, 5), (10, 11), (12, 14), (13, 20)],
            [(0, 11), (12, 20)],
        ),
        (
            [(0, 10), (19, 21), (18, 20), (12, 13)],
            [(0, 10), (12, 13), (18, 21)],
        ),
        (
            [(0, 10)],
            [(0, 10)],
        ),
        (
            [],
            [],
        ),
    ],
)
def test_merge_cookie_ranges(cookie_ranges, merged) -> None:
    """Test merge_cookie_ranges."""
    assert merge_cookie_ranges(cookie_ranges) == merged


@pytest.mark.parametrize(
    "cookies,expected",
    [
        (
            [1, 2, 4, 5],
            [(1, 2), (4, 5)],
        ),
        (
            [],
            [],
        ),
    ],
)
def test_map_cookie_list_as_tuples(cookies, expected) -> None:
    """Test map_cookie_list_as_tuples."""
    assert map_cookie_list_as_tuples(cookies) == expected


def test_map_cookie_list_as_tuples_fail() -> None:
    """Test map_cookie_list_as_tuples."""
    with pytest.raises(ValueError) as exc:
        map_cookie_list_as_tuples([1, 2, 3])
    assert "to be even" in str(exc)


@pytest.mark.parametrize(
    "command,mock_method",
    [
        ("add", "as_of_add_flow_mod"),
        ("delete", "as_of_delete_flow_mod"),
        ("delete_strict", "as_of_strict_delete_flow_mod"),
    ],
)
def test_build_flow_mod_from_command(command, mock_method):
    """Test build_flow_mod_from_command."""
    mock = MagicMock()
    build_flow_mod_from_command(mock, command)
    assert getattr(mock, mock_method).call_count == 1


@pytest.mark.parametrize(
    "cookie,cookie_mask,should_raise",
    [
        (0x64, 0xFF, False),
        (0x64, None, True),
        (None, 0xFF, True),
        (None, None, False),
    ],
)
def test_validate_cookies_del(cookie, cookie_mask, should_raise):
    """Test validate_cookies_del."""
    flow = {}
    if cookie:
        flow["cookie"] = cookie
    if cookie_mask:
        flow["cookie_mask"] = cookie_mask

    if should_raise:
        with pytest.raises(ValueError) as exc:
            validate_cookies_del([flow])
        assert str(exc)
    else:
        assert not validate_cookies_del([flow])


@pytest.mark.parametrize(
    "cookie,cookie_mask,should_raise",
    [
        (0x64, 0xFF, True),
        (0x64, None, False),
        (None, 0xFF, True),
        (None, None, False),
    ],
)
def test_validate_cookies_add(cookie, cookie_mask, should_raise):
    """Test validate_cookies_add."""
    flow = {}
    if cookie:
        flow["cookie"] = cookie
    if cookie_mask:
        flow["cookie_mask"] = cookie_mask

    if should_raise:
        with pytest.raises(ValueError) as exc:
            validate_cookies_add([flow])
        assert str(exc)
    else:
        assert not validate_cookies_add([flow])


class TestUtils(TestCase):
    """Test Utils."""

    def test_validate_range_exceptions(self):
        """Test _validate_range exceptions."""

        test_data = [((1,), ValueError), ((2, 1), ValueError), ((1, "1"), TypeError)]
        for values, exception in test_data:
            with self.subTest(values=values, exception=exception):
                with self.assertRaises(exception) as exc:
                    _validate_range(values)

                assert str(exc)

    def test_valid_consistency_ignored_false_cases(self):
        """Test _valid_consistency_ignored False cases."""

        test_data = [[(1,)], ["2"]]
        for values in test_data:
            with self.subTest(values=values):
                assert not _valid_consistency_ignored(values)

    def test_get_min_wait_diff_early_return(self):
        """Test get_min_wait diff early return."""
        test_data = [
            (timedelta(seconds=1), timedelta(seconds=2), 3),
            (timedelta(seconds=4), timedelta(seconds=3), 0),
            (timedelta(seconds=8), timedelta(seconds=2), 4),
        ]
        for dt_t2, dt_t1, min_wait in test_data:
            with self.subTest(dt_t2=dt_t2, dt_t1=dt_t1, min_wait=min_wait):
                assert get_min_wait_diff(dt_t2, dt_t1, min_wait) == 0

    def test_get_min_wait_diff(self):
        """Test get_min_wait diff values."""
        test_data = [
            (timedelta(seconds=3), timedelta(seconds=2), 4),
            (timedelta(seconds=5), timedelta(seconds=2), 6),
        ]
        for dt_t2, dt_t1, min_wait in test_data:
            with self.subTest(dt_t2=dt_t2, dt_t1=dt_t1, min_wait=min_wait):
                assert (
                    get_min_wait_diff(dt_t2, dt_t1, min_wait)
                    == min_wait - (dt_t2 - dt_t1).total_seconds()
                )

    @patch("napps.kytos.flow_manager.utils.log")
    def test_flows_to_log_info(self, mock_log):
        """Test flows_to_log_info"""
        flows = list(range(500))
        flows_to_log_info("", flows, maximum=200)
        assert mock_log.info.call_count == 3
