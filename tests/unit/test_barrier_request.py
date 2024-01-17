"""Module to test the barrier request module."""

from napps.kytos.flow_manager.barrier_request import new_barrier_request
from pyof.v0x04.controller2switch.barrier_request import BarrierRequest as BReq13
import pytest


class TestBarrierRkquest:
    """Test barrier request."""

    @pytest.mark.parametrize("version, expected_class", [(0x04, BReq13)])
    def test_new_barrier_request(self, version, expected_class):
        """Test new_barrier_request."""

        assert isinstance(new_barrier_request(version), expected_class)
