"""Module to test the utils module."""
from datetime import timedelta
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from napps.kytos.flow_manager.exceptions import InvalidCommandError
from napps.kytos.flow_manager.utils import (
    _valid_consistency_ignored,
    _validate_range,
    build_command_from_flow_mod,
    build_flow_mod_from_command,
    get_min_wait_diff,
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
def tet_build_command_from_flow_mod(value, expected):
    """Test build_command_from_flow_mod."""
    assert build_command_from_flow_mod(value) == expected


def test_build_flow_mod_from_command_exc():
    """test build_flow_mod_from_command."""
    with pytest.raises(InvalidCommandError):
        build_flow_mod_from_command(MagicMock(), "invalid_command")


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
