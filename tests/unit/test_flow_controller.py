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
            (
                "flows",
                [
                    ("switch", 1),
                    ("flow.cookie", 1),
                    ("state", 1),
                    ("inserted_at", 1),
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

    def test_upsert_flow(self) -> None:
        """Test upsert_flow."""
        assert self.flow_controller.upsert_flow(self.match_id, self.flow_dict)
        arg1, arg2 = self.flow_controller.db.flows.find_one_and_update.call_args[0]
        assert arg1 == {"_id": self.match_id}
        assert arg2["$set"]["flow"]

    def test_update_flow_state(self) -> None:
        """Test update_flow_state."""
        assert self.flow_controller.update_flow_state(self.flow_id, "installed")
        arg1, arg2 = self.flow_controller.db.flows.find_one_and_update.call_args[0]
        assert arg1 == {"flow_id": self.flow_id}
        assert arg2["$set"]["state"] == "installed"

    def test_update_flows_state(self) -> None:
        """Test update_flows_state."""
        assert self.flow_controller.update_flows_state([self.flow_id], "installed")
        arg1, arg2 = self.flow_controller.db.flows.update_many.call_args[0]
        assert arg1 == {"flow_id": {"$in": [self.flow_id]}}
        assert arg2["$set"]["state"] == "installed"

    def test_delete_flows_by_ids(self) -> None:
        """Test delete_flows_by_ids."""
        assert self.flow_controller.delete_flows_by_ids([self.flow_id])
        args = self.flow_controller.db.flows.delete_many.call_args[0]
        assert args[0] == {"flow_id": {"$in": [self.flow_id]}}

    def test_delete_flow_by_id(self) -> None:
        """Test delete_flow_by_id."""
        assert self.flow_controller.delete_flow_by_id(self.flow_id)
        args = self.flow_controller.db.flows.delete_one.call_args[0]
        assert args[0] == {"flow_id": self.flow_id}

    def test_get_flows_lte_inserted_at(self) -> None:
        """Test get_flows_lte_inserted_at."""
        dt = datetime.utcnow()
        flows = list(self.flow_controller.get_flows_lte_inserted_at(self.dpid, dt))
        assert not flows
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0] == {
            "inserted_at": {"$lte": dt},
            "switch": self.dpid,
        }

    def test_get_flows(self) -> None:
        """Test get_flows."""
        assert not list(self.flow_controller.get_flows(self.dpid))
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0] == {"switch": self.dpid}

    def test_get_flows_by_cookie(self) -> None:
        """Test get_flows_by_cookie."""
        cookie = 0
        assert not list(self.flow_controller.get_flows_by_cookie(self.dpid, cookie))
        args = self.flow_controller.db.flows.find.call_args[0]
        assert args[0] == {
            "switch": self.dpid,
            "flow.cookie": Decimal128(Decimal(cookie)),
        }

    def test_get_flows_by_state(self) -> None:
        """Test get_flows_by_cookie."""
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

    def test_get_flow_check_gte_updated_at(self) -> None:
        """Test get_flow_check_gte_updated_at."""
        dt = datetime.utcnow()
        state = "active"
        assert self.flow_controller.get_flow_check_gte_updated_at(
            self.dpid, dt, state=state
        )
        args = self.flow_controller.db.flow_checks.find_one.call_args[0]
        assert args[0] == {"_id": self.dpid, "state": state, "updated_at": {"$gte": dt}}
