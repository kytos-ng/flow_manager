"""Module to test the utils module."""
# pylint: disable=import-error
import pytest
from napps.kytos.flow_manager.match import match_flow
from napps.kytos.flow_manager.v0x04.match import _match_cookie, match13_no_strict


@pytest.mark.parametrize(
    "to_install,stored,should_match",
    [
        (
            {"match": {"in_port": 1}},
            {
                "priority": 10,
                "match": {
                    "in_port": 1,
                    "dl_vlan": 100,
                },
            },
            True,
        ),
        (
            {"match": {"in_port": 1}},
            {
                "priority": 10,
                "match": {
                    "in_port": 2,
                    "dl_vlan": 100,
                },
            },
            False,
        ),
        (
            {"match": {"in_port": 5, "dl_vlan": 3201}},
            {
                "cookie": 0,
                "match": {"dl_src": "ee:ee:ee:ee:ee:02"},
                "priority": 50000,
            },
            False,
        ),
    ],
)
def test_no_strict_delete_in_port(to_install, stored, should_match) -> None:
    """test_no_strict_delete_in_port."""
    assert bool(match13_no_strict(to_install, stored)) == should_match


@pytest.mark.parametrize(
    "to_install,stored,should_match",
    [
        (
            {"cookie": 0x10, "cookie_mask": 0xFF},
            {"cookie": 0x20, "cookie_mask": 0xFF},
            False,
        ),
        (
            {"cookie": 0x10, "cookie_mask": 0xFF},
            {"cookie": 0x10, "cookie_mask": 0xFF},
            True,
        ),
        (
            {"cookie": 0x11, "cookie_mask": 0x0F},
            {"cookie": 0x21, "cookie_mask": 0x0F},
            True,
        ),
    ],
)
def test_match_cookie(to_install, stored, should_match):
    """Test _match_cookie."""
    assert _match_cookie(to_install, stored) == should_match


@pytest.mark.parametrize(
    "to_install,stored,should_match",
    [
        (
            {"match": {}},
            {"match": {"in_port": 1}},
            True,
        ),
        (
            {"match": {}, "cookie": 0x20, "cookie_mask": 0xFF},
            {"match": {"in_port": 1}},
            False,
        ),
    ],
)
def test_empty_match(to_install, stored, should_match) -> None:
    """test empty match."""
    assert bool(match13_no_strict(to_install, stored)) == should_match


@pytest.mark.parametrize(
    "to_install,stored,should_match",
    [
        (
            {"cookie": 0x10, "cookie_mask": 0xFF},
            {"cookie": 0x20, "cookie_mask": 0xFF},
            False,
        ),
        (
            {"match": {"ipv4_src": "192.168.1.1", "ipv4_dst": "1.1.1.1"}},
            {"match": {"ipv4_src": "192.168.1.2"}},
            False,
        ),
    ],
)
def test_match_no_strict_return_false_cases(to_install, stored, should_match):
    """Test match_no_strict return False cases that haven't been covered yet."""
    assert bool(match13_no_strict(to_install, stored)) == should_match


def test_match_func_calls() -> None:
    """Test match func calls."""
    assert match_flow({}, 0x04, {}) == match13_no_strict({}, {})
    with pytest.raises(NotImplementedError):
        match_flow({}, 0x20, {})
