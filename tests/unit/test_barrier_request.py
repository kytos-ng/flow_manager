"""Module to test the barrier request module."""
from unittest import TestCase

from napps.kytos.flow_manager.barrier_request import new_barrier_request
from pyof.v0x01.controller2switch.barrier_request import BarrierRequest as BReq10
from pyof.v0x04.controller2switch.barrier_request import BarrierRequest as BReq13


class TestBarrierRkquest(TestCase):
    """Test barrier request."""

    def test_new_barrier_request(self):
        """Test new_barrier_request."""

        test_data = [(0x01, BReq10), (0x04, BReq13)]
        for version, expected_class in test_data:
            with self.subTest(version=version, expected_class=expected_class):
                assert isinstance(new_barrier_request(version), expected_class)
