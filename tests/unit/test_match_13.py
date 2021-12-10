"""Module to test the utils module."""
from unittest import TestCase

from napps.kytos.flow_manager.v0x04.match import (
    _match_cookie,
    match13_no_strict,
    match13_strict,
)
from napps.kytos.flow_manager.match import match_flow, match_strict_flow


class TestMatchOF13(TestCase):
    """Test match for OF13."""

    def test_match_cookie(self):
        """Test _match_cookie."""

        test_data = [
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
        ]
        for flow1, flow2, should_match in test_data:
            with self.subTest(flow1=flow1, flow2=flow2, should_match=should_match):
                assert _match_cookie(flow1, flow2) == should_match

    def test_match_no_strict_return_false_cases(self):
        """Test match_no_strict return False cases that haven't been covered yet."""

        test_data = [
            (
                {"cookie": 0x10, "cookie_mask": 0xFF},
                {"cookie": 0x20, "cookie_mask": 0xFF},
            ),
            (
                {"match": {"ipv4_src": "192.168.1.1", "ipv4_dst": "1.1.1.1"}},
                {"match": {"ipv4_src": "192.168.1.2"}},
            ),
        ]
        for flow_to_install, flow_stored in test_data:
            with self.subTest(flow_to_install=flow_to_install, flow_stored=flow_stored):
                assert not match13_no_strict(flow_to_install, flow_stored)

    def test_match_strict_return_false_cases(self):
        """Test match_strict return False cases that haven't been covered yet."""

        test_data = [
            (
                {"cookie": 0x10, "cookie_mask": 0xFF},
                {"cookie": 0x20, "cookie_mask": 0xFF},
            ),
            (
                {"match": {"ipv4_src": "192.168.1.1"}},
                {"match_wrong_key": {"ipv4_src": "192.168.1.2"}},
            ),
            (
                {"match_wrong_key": {"ipv4_src": "192.168.1.2"}},
                {"match": {"ipv4_src": "192.168.1.1"}},
            ),
            (
                {"match": {"ipv4_src": "192.168.1.2"}},
                {"match": {"ipv4_src": "192.168.1.1"}},
            ),
        ]
        for flow_to_install, flow_stored in test_data:
            with self.subTest(flow_to_install=flow_to_install, flow_stored=flow_stored):
                assert not match13_strict(flow_to_install, flow_stored)

    def test_match_strict_positive_cases(self):
        """Test match_strict positive cases that haven't been covered yet."""

        test_data = [
            (
                {"match_wrong_key": {"ipv4_src": "192.168.1.2"}},
                {"match_wrong_key": {"ipv4_src": "192.168.1.1"}},
            ),
        ]
        for flow_to_install, flow_stored in test_data:
            with self.subTest(flow_to_install=flow_to_install, flow_stored=flow_stored):
                assert match13_strict(flow_to_install, flow_stored)

    def test_match_strict_raises_implemented_error(self):
        """Test match no strict raises implemented error for unsupported versions."""

        test_data = [0x02, 0x03, 0x05, 0x06]
        test_data = [
            [(version, match_flow), (version, match_strict_flow)]
            for version in test_data
        ]
        for tuples in test_data:
            for of_version, func in tuples:
                with self.subTest(of_version=of_version, func=func):
                    with self.assertRaises(NotImplementedError) as exc:
                        func({}, of_version, {})
                    assert str(exc)
