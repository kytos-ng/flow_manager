"""Module to test FlowController."""
# pylint: disable=invalid-name,relative-beyond-top-level

from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock

from bson.decimal128 import Decimal128
from napps.kytos.flow_manager.controllers import FlowController


class TestFlowController(TestCase):  # pylint: disable=too-many-public-methods
    """Test the Main class."""

    def setUp(self) -> None:
        """Execute steps before each tests."""
        self.flow_controller = FlowController(MagicMock())
        self.dpid = "00:00:00:00:00:00:00:01"
        self.match_id = "adb1343e8648d24e7c2b89796b300fa3"
        self.flow_id = "06e034636d620e8b12807bedcbb80a7d"
        self.flow_dict = {
            "switch": self.dpid,
            "flow_id": self.flow_id,
            "flow": {
                "match": {"in_port": 1, "dl_vlan": 105},
                "actions": [{"action_type": "output", "port": 3}],
            },
        }

    def test_boostrap_indexes(self) -> None:
        """Test_boostrap_indexes."""
        self.flow_controller.bootstrap_indexes()

        expected_indexes = [
            ("flows", [("flow_id", 1)]),
            ("flows", [("flow.cookie", 1)]),
            ("flows", [("state", 1)]),
            (
                "flows",
                [
                    ("switch", 1),
                    ("flow.cookie", 1),
                    ("state", 1),
                    ("inserted_at", 1),
                    ("updated_at", 1),
                ],
            ),
            (
                "flow_checks",
                [
                    ("state", 1),
                    ("updated_at", 1),
                ],
            ),
        ]
        mock = self.flow_controller.mongo.bootstrap_index
        assert mock.call_count == len(expected_indexes)
        indexes = [(v[0][0], v[0][1]) for v in mock.call_args_list]
        assert expected_indexes == indexes

    def test_upsert_flows(self) -> None:
        """Test upsert_flows."""
        match_ids, flow_dicts = ["1", "2"], [
            {"flow_id": "1", "switch": self.dpid, "flow": {"match": {"in_port": 1}}},
            {"flow_id": "2", "switch": self.dpid, "flow": {"match": {"in_port": 2}}},
        ]
        assert self.flow_controller.upsert_flows(match_ids, flow_dicts)
        assert self.flow_controller.db.flows.bulk_write.call_count == 1
        args = self.flow_controller.db.flows.bulk_write.call_args[0]
        assert len(args[0]) == len(flow_dicts)

    def test_update_flows_state(self) -> None:
        """Test update_flows_state."""
        assert self.flow_controller.update_flows_state([self.flow_id], "installed")
        arg1, arg2 = self.flow_controller.db.flows.update_many.call_args[0]
        assert arg1 == {"flow_id": {"$in": [self.flow_id]}}
        assert arg2["$set"]["state"] == "installed"

    def test_delete_flow_by_id(self) -> None:
        """Test delete_flow_by_id."""
        assert self.flow_controller.delete_flow_by_id(self.flow_id)
        args = self.flow_controller.db.flows.delete_one.call_args[0]
        assert args[0] == {"flow_id": self.flow_id}

    def test_get_flows_lte_updated_at(self) -> None:
        """Test get_flows_lte_updated_at."""
        dt = datetime.utcnow()
        flows = list(self.flow_controller.get_flows_lte_updated_at(self.dpid, dt))
        assert not flows
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0] == {
            "updated_at": {"$lte": dt},
            "state": {"$ne": "deleted"},
            "switch": self.dpid,
        }
        args = self.flow_controller.db.flows.find(
            {"inserted_at": {"lte": dt}, "switch": self.dpid}
        ).sort.call_args[0]
        assert args == ("inserted_at", 1)

    def test_get_flows(self) -> None:
        """Test get_flows."""
        assert not list(self.flow_controller.get_flows(self.dpid))
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0] == {"switch": self.dpid, "state": {"$ne": "deleted"}}

    def test_get_flows_by_cookie_ranges(self) -> None:
        """Test get_flows_by_cookie_ranges."""
        cookie_ranges = [(0x64, 0x65)]
        assert not list(
            self.flow_controller.get_flows_by_cookie_ranges([self.dpid], cookie_ranges)
        )
        args = self.flow_controller.db.flows.aggregate.call_args[0]
        assert args[0][0]["$match"] == {
            "switch": {"$in": [self.dpid]},
            "state": {"$ne": "deleted"},
            "$or": [
                {
                    "flow.cookie": {
                        "$gte": Decimal128(Decimal(cookie_ranges[0][0])),
                        "$lte": Decimal128(Decimal(cookie_ranges[0][1])),
                    }
                }
            ],
        }

    def test_get_flows_by_state(self) -> None:
        """Test get_flows_by_state."""
        state = "installed"
        assert not list(self.flow_controller.get_flows_by_state(self.dpid, state))
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0] == {"switch": self.dpid, "state": "installed"}

    def test_upsert_flow_check(self) -> None:
        """Test upsert_flow_check."""
        assert self.flow_controller.upsert_flow_check(self.dpid, "active")
        args = self.flow_controller.db.flow_checks.find_one_and_update.call_args[0]
        assert args[0] == {"_id": self.dpid}
        assert args[1]["$set"]["state"] == "active"

    def test_get_flow_check(self) -> None:
        """Test get_flow_check."""
        state = "active"
        assert self.flow_controller.get_flow_check(self.dpid, state=state)
        args = self.flow_controller.db.flow_checks.find_one.call_args[0]
        assert args[0] == {"_id": self.dpid, "state": state}

    def test_find_flows(self) -> None:
        """Test find_flows."""
        state = "installed"
        cookie_range = [84114963, 84114965]
        assert not list(
            self.flow_controller.find_flows(
                dpids=[self.dpid], state=state, cookie_range=cookie_range
            )
        )
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0]["switch"]["$in"] == [self.dpid]
        assert args[0]["state"] == "installed"
        assert args[0]["flow.cookie"]["$gte"] == Decimal128(Decimal(cookie_range[0]))
        assert args[0]["flow.cookie"]["$lte"] == Decimal128(Decimal(cookie_range[1]))
