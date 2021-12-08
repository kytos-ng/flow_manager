"""Test Main methods."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

# pylint: disable=too-many-lines,fixme
# TODO split this test suite in smaller ones

from kytos.core.helpers import now
from kytos.lib.helpers import (
    get_connection_mock,
    get_controller_mock,
    get_kytos_event_mock,
    get_switch_mock,
    get_test_client,
)


# pylint: disable=protected-access, too-many-public-methods
class TestMain(TestCase):
    """Tests for the Main class."""

    API_URL = "http://localhost:8181/api/kytos/flow_manager"

    def setUp(self):
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.kytos.flow_manager.main import Main

        self.addCleanup(patch.stopall)

        controller = get_controller_mock()
        self.switch_01 = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        self.switch_01.is_enabled.return_value = True
        self.switch_01.flows = []

        self.switch_02 = get_switch_mock("00:00:00:00:00:00:00:02", 0x04)
        self.switch_02.is_enabled.return_value = False
        self.switch_02.flows = []

        controller.switches = {
            "00:00:00:00:00:00:00:01": self.switch_01,
            "00:00:00:00:00:00:00:02": self.switch_02,
        }

        self.napp = Main(controller)

    def test_rest_list_without_dpid(self):
        """Test list rest method withoud dpid."""
        flow_dict = {
            "priority": 13,
            "cookie": 84114964,
            "command": "add",
            "match": {"dl_dst": "00:15:af:d5:38:98"},
        }
        flow_dict_2 = {
            "priority": 18,
            "cookie": 84114964,
            "command": "add",
            "match": {"dl_dst": "00:15:af:d5:38:98"},
        }
        flow_1 = MagicMock()
        flow_1.as_dict.return_value = flow_dict
        flow_2 = MagicMock()
        flow_2.as_dict.return_value = flow_dict_2
        self.switch_01.flows.append(flow_1)
        self.switch_02.flows.append(flow_2)

        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/flows"

        response = api.get(url)
        expected = {
            "00:00:00:00:00:00:00:01": {"flows": [flow_dict]},
            "00:00:00:00:00:00:00:02": {"flows": [flow_dict_2]},
        }
        self.assertEqual(response.json, expected)
        self.assertEqual(response.status_code, 200)

    def test_rest_list_with_dpid(self):
        """Test list rest method with dpid."""
        flow_dict = {
            "priority": 13,
            "cookie": 84114964,
            "command": "add",
            "match": {"dl_dst": "00:15:af:d5:38:98"},
        }
        flow_1 = MagicMock()
        flow_1.as_dict.return_value = flow_dict
        self.switch_01.flows.append(flow_1)

        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/flows/00:00:00:00:00:00:00:01"

        response = api.get(url)
        expected = {"00:00:00:00:00:00:00:01": {"flows": [flow_dict]}}

        self.assertEqual(response.json, expected)
        self.assertEqual(response.status_code, 200)

    def test_list_flows_fail_case(self):
        """Test the failure case to recover all flows from a switch by dpid.

        Failure case: Switch not found.
        """
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/flows/00:00:00:00:00:00:00:05"
        response = api.get(url)
        self.assertEqual(response.status_code, 404)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_rest_add_and_delete_without_dpid(self, mock_install_flows):
        """Test add and delete rest method without dpid."""
        api = get_test_client(self.napp.controller, self.napp)

        for method in ["flows", "delete"]:
            url = f"{self.API_URL}/v2/{method}"

            response_1 = api.post(url, json={"flows": [{"priority": 25}]})
            response_2 = api.post(url)

            self.assertEqual(response_1.status_code, 202)
            self.assertEqual(response_2.status_code, 400)

        self.assertEqual(mock_install_flows.call_count, 2)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_rest_add_and_delete_with_dpid(self, mock_install_flows):
        """Test add and delete rest method with dpid."""
        api = get_test_client(self.napp.controller, self.napp)
        data = {"flows": [{"priority": 25}]}
        for method in ["flows", "delete"]:
            url_1 = f"{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:01"
            url_2 = f"{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:02"

            response_1 = api.post(url_1, json=data)
            response_2 = api.post(url_2, json=data)

            self.assertEqual(response_1.status_code, 202)
            if method == "delete":
                self.assertEqual(response_2.status_code, 202)

        self.assertEqual(mock_install_flows.call_count, 3)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_rest_add_and_delete_with_dpi_fail(self, mock_install_flows):
        """Test fail case the add and delete rest method with dpid."""
        api = get_test_client(self.napp.controller, self.napp)
        data = {"flows": [{"priority": 25}]}
        for method in ["flows", "delete"]:
            url_1 = f"{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:01"
            url_2 = f"{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:02"
            url_3 = f"{self.API_URL}/v2/{method}/00:00:00:00:00:00:00:03"

            response_1 = api.post(url_1)
            response_2 = api.post(url_2, data=data)
            response_3 = api.post(url_2, json={})
            response_4 = api.post(url_3, json=data)

            self.assertEqual(response_1.status_code, 400)
            self.assertEqual(response_2.status_code, 415)
            self.assertEqual(response_3.status_code, 400)
            self.assertEqual(response_4.status_code, 404)

        self.assertEqual(mock_install_flows.call_count, 0)

    def test_get_all_switches_enabled(self):
        """Test _get_all_switches_enabled method."""
        switches = self.napp._get_all_switches_enabled()

        self.assertEqual(switches, [self.switch_01])

    @patch("napps.kytos.flow_manager.main.Main._store_changed_flows")
    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    @patch("napps.kytos.flow_manager.main.Main._add_flow_mod_sent")
    @patch("napps.kytos.flow_manager.main.Main._send_flow_mod")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_install_flows(self, *args):
        """Test _install_flows method."""
        (
            mock_flow_factory,
            mock_send_flow_mod,
            mock_add_flow_mod_sent,
            mock_send_napp_event,
            _,
        ) = args
        serializer = MagicMock()
        flow = MagicMock()
        flow_mod = MagicMock()

        flow.as_of_add_flow_mod.return_value = flow_mod
        serializer.from_dict.return_value = flow
        mock_flow_factory.return_value = serializer

        flows_dict = {"flows": [MagicMock()]}
        switches = [self.switch_01]
        self.napp._install_flows("add", flows_dict, switches)

        mock_send_flow_mod.assert_called_with(flow.switch, flow_mod)
        mock_add_flow_mod_sent.assert_called_with(flow_mod.header.xid, flow, "add")
        mock_send_napp_event.assert_called_with(self.switch_01, flow, "add")

    @patch("napps.kytos.flow_manager.main.Main._store_changed_flows")
    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    @patch("napps.kytos.flow_manager.main.Main._add_flow_mod_sent")
    @patch("napps.kytos.flow_manager.main.Main._send_flow_mod")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_install_flows_with_delete_strict(self, *args):
        """Test _install_flows method with strict delete command."""
        (
            mock_flow_factory,
            mock_send_flow_mod,
            mock_add_flow_mod_sent,
            mock_send_napp_event,
            _,
        ) = args
        serializer = MagicMock()
        flow = MagicMock()
        flow_mod = MagicMock()

        flow.as_of_strict_delete_flow_mod.return_value = flow_mod
        serializer.from_dict.return_value = flow
        mock_flow_factory.return_value = serializer

        flows_dict = {"flows": [MagicMock()]}
        switches = [self.switch_01]
        self.napp._install_flows("delete_strict", flows_dict, switches)

        mock_send_flow_mod.assert_called_with(flow.switch, flow_mod)
        mock_add_flow_mod_sent.assert_called_with(
            flow_mod.header.xid, flow, "delete_strict"
        )
        mock_send_napp_event.assert_called_with(self.switch_01, flow, "delete_strict")

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_event_add_flow(self, mock_install_flows):
        """Test method for installing flows on the switches through events."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid)
        self.napp.controller.switches = {dpid: switch}
        mock_flow_dict = MagicMock()
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.install",
            content={"dpid": dpid, "flow_dict": mock_flow_dict},
        )
        self.napp.event_flows_install_delete(event)
        mock_install_flows.assert_called_with("add", mock_flow_dict, [switch])

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_event_flows_install_delete(self, mock_install_flows):
        """Test method for removing flows on the switches through events."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid)
        self.napp.controller.switches = {dpid: switch}
        mock_flow_dict = MagicMock()
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.delete",
            content={"dpid": dpid, "flow_dict": mock_flow_dict},
        )
        self.napp.event_flows_install_delete(event)
        mock_install_flows.assert_called_with("delete", mock_flow_dict, [switch])

    def test_add_flow_mod_sent(self):
        """Test _add_flow_mod_sent method."""
        xid = 0
        flow = MagicMock()

        self.napp._add_flow_mod_sent(xid, flow, "add")

        self.assertEqual(self.napp._flow_mods_sent[xid], (flow, "add"))

    @patch("kytos.core.buffers.KytosEventBuffer.put")
    def test_send_flow_mod(self, mock_buffers_put):
        """Test _send_flow_mod method."""
        switch = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        flow_mod = MagicMock()

        self.napp._send_flow_mod(switch, flow_mod)

        mock_buffers_put.assert_called()

    @patch("kytos.core.buffers.KytosEventBuffer.put")
    def test_send_napp_event(self, mock_buffers_put):
        """Test _send_napp_event method."""
        switch = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        flow = MagicMock()

        for command in ["add", "delete", "delete_strict", "error"]:
            self.napp._send_napp_event(switch, flow, command)

        self.assertEqual(mock_buffers_put.call_count, 4)

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_handle_errors(self, mock_send_napp_event):
        """Test handle_errors method."""
        flow = MagicMock()
        self.napp._flow_mods_sent[0] = (flow, "add")

        switch = get_switch_mock("00:00:00:00:00:00:00:01")
        switch.connection = get_connection_mock(
            0x04, get_switch_mock("00:00:00:00:00:00:00:02")
        )

        protocol = MagicMock()
        protocol.unpack.return_value = "error_packet"

        switch.connection.protocol = protocol

        message = MagicMock()
        message.header.xid.value = 0
        message.error_type = 2
        message.code = 5
        event = get_kytos_event_mock(
            name=".*.of_core.*.ofpt_error",
            content={"message": message, "source": switch.connection},
        )
        self.napp.handle_errors(event)

        mock_send_napp_event.assert_called_with(
            flow.switch,
            flow,
            "error",
            error_command="add",
            error_code=5,
            error_type=2,
        )

    @patch("napps.kytos.flow_manager.main.StoreHouse.get_data")
    def test_load_flows(self, mock_storehouse):
        """Test load flows."""
        self.napp._load_flows()
        mock_storehouse.assert_called()

    @patch("napps.kytos.flow_manager.main.ENABLE_CONSISTENCY_CHECK", False)
    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_resend_stored_flows(self, mock_install_flows):
        """Test resend stored flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        mock_event = MagicMock()
        flow = {"command": "add", "flow": MagicMock()}

        mock_event.content = {"switch": switch}
        self.napp.controller.switches = {dpid: switch}
        self.napp.stored_flows = {dpid: {0: [flow]}}
        self.napp.resend_stored_flows(mock_event)
        mock_install_flows.assert_called()

    @patch("napps.kytos.of_core.flow.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_store_changed_flows(self, mock_save_flow, _):
        """Test store changed flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow = {
            "priority": 17,
            "cookie": 84114964,
            "command": "add",
            "match": {"dl_dst": "00:15:af:d5:38:98"},
        }
        match_fields = {
            "priority": 17,
            "cookie": 84114964,
            "command": "add",
            "dl_dst": "00:15:af:d5:38:98",
        }
        flows = {"flow": flow}

        command = "add"
        stored_flows = {
            84114964: [
                {
                    "match_fields": match_fields,
                    "flow": flow,
                }
            ]
        }
        self.napp.stored_flows = {dpid: stored_flows}
        self.napp._store_changed_flows(command, flows, switch)
        mock_save_flow.assert_called()

        self.napp.stored_flows = {}
        self.napp._store_changed_flows(command, flows, switch)
        mock_save_flow.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_check_switch_consistency_add(self, *args):
        """Test check_switch_consistency method.

        This test checks the case when a flow is missing in switch and have the
        ADD command.
        """
        (mock_flow_factory, mock_install_flows) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.flows = []

        flow_1 = MagicMock()
        flow_1.as_dict.return_value = {"flow_1": "data"}

        stored_flows = [{"flow": {"flow_1": "data"}}]
        serializer = MagicMock()
        serializer.flow.cookie.return_value = 0

        mock_flow_factory.return_value = serializer
        self.napp.stored_flows = {dpid: {0: stored_flows}}
        self.napp.check_switch_consistency(switch)
        mock_install_flows.assert_called()

    @patch("napps.kytos.flow_manager.storehouse.StoreHouse.save_flow")
    def test_add_overlapping_flow(self, *args):
        """Test add an overlapping flow."""
        (_,) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        cookie = 0x20

        self.napp.stored_flows = {
            dpid: {
                cookie: [
                    {
                        "flow": {
                            "priority": 10,
                            "cookie": 84114904,
                            "match": {
                                "ipv4_src": "192.168.1.1",
                                "ipv4_dst": "192.168.0.2",
                            },
                            "actions": [{"action_type": "output", "port": 2}],
                        }
                    }
                ]
            }
        }

        new_actions = [{"action_type": "output", "port": 3}]
        flow_dict = {
            "priority": 10,
            "cookie": cookie,
            "match": {
                "ipv4_src": "192.168.1.1",
                "ipv4_dst": "192.168.0.2",
            },
            "actions": new_actions,
        }

        self.napp._add_flow_store(flow_dict, switch)
        assert len(self.napp.stored_flows[dpid]) == 1
        assert self.napp.stored_flows[dpid][0x20][0]["flow"]["actions"] == new_actions

    @patch("napps.kytos.flow_manager.storehouse.StoreHouse.save_flow")
    def test_add_overlapping_flow_multiple_stored(self, *args):
        """Test add an overlapping flow with multiple flows stored."""
        (_,) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        cookie = 0x20

        stored_flows_list = [
            {
                "flow": {
                    "actions": [{"action_type": "output", "port": 2}],
                    "match": {"dl_vlan": 100, "in_port": 1},
                    "priority": 10,
                },
            },
            {
                "flow": {
                    "actions": [{"action_type": "output", "port": 3}],
                    "match": {"dl_vlan": 200, "in_port": 1},
                    "priority": 10,
                },
            },
            {
                "flow": {
                    "actions": [{"action_type": "output", "port": 4}],
                    "match": {"dl_vlan": 300, "in_port": 1},
                    "priority": 10,
                },
            },
            {
                "flow": {
                    "actions": [{"action_type": "output", "port": 4}],
                    "match": {"in_port": 1},
                    "priority": 10,
                },
            },
        ]

        self.napp.stored_flows = {dpid: {cookie: list(stored_flows_list)}}

        new_actions = [{"action_type": "output", "port": 3}]
        overlapping_flow = {
            "priority": 10,
            "cookie": cookie,
            "match": {
                "in_port": 1,
            },
            "actions": new_actions,
        }

        self.napp._add_flow_store(overlapping_flow, switch)
        assert len(self.napp.stored_flows[dpid][cookie]) == len(stored_flows_list)

        # only the last flow is expected to be strictly matched
        self.assertDictEqual(
            self.napp.stored_flows[dpid][cookie][len(stored_flows_list) - 1]["flow"],
            overlapping_flow,
        )

        # all flows except the last one should still be the same
        for i in range(0, len(stored_flows_list) - 1):
            self.assertDictEqual(
                self.napp.stored_flows[dpid][cookie][i], stored_flows_list[i]
            )

    @patch("napps.kytos.flow_manager.storehouse.StoreHouse.save_flow")
    def test_add_overlapping_flow_diff_priority(self, *args):
        """Test that a different priority wouldn't overlap."""
        (_,) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid

        cookie = 0x20
        self.napp.stored_flows = {
            dpid: {
                cookie: [
                    {
                        "flow": {
                            "priority": 10,
                            "cookie": 84114904,
                            "match": {
                                "ipv4_src": "192.168.1.1",
                                "ipv4_dst": "192.168.0.2",
                            },
                            "actions": [{"action_type": "output", "port": 2}],
                        }
                    }
                ]
            }
        }

        new_actions = [{"action_type": "output", "port": 3}]
        flow_dict = {
            "priority": 11,
            "cookie": cookie,
            "match": {
                "ipv4_src": "192.168.1.1",
                "ipv4_dst": "192.168.0.2",
            },
            "actions": new_actions,
        }

        self.napp._add_flow_store(flow_dict, switch)
        assert len(self.napp.stored_flows[dpid][cookie]) == 2

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_check_switch_flow_not_missing(self, *args):
        """Test check_switch_consistency method.

        This test checks the case when flow is not missing.
        """
        (mock_flow_factory, mock_install_flows) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)

        flow_1 = MagicMock()
        flow_dict = {
            "flow": {
                "priority": 10,
                "cookie": 84114904,
                "match": {
                    "ipv4_src": "192.168.1.1",
                    "ipv4_dst": "192.168.0.2",
                },
                "actions": [],
            }
        }
        flow_1.cookie = 84114904
        flow_1.as_dict.return_value = flow_dict

        serializer = MagicMock()
        serializer.from_dict.return_value = flow_1

        switch.flows = [flow_1]
        mock_flow_factory.return_value = serializer
        self.napp.stored_flows = {
            dpid: {
                84114904: [
                    {
                        "flow": {
                            "priority": 10,
                            "cookie": 84114904,
                            "match": {
                                "ipv4_src": "192.168.1.1",
                                "ipv4_dst": "192.168.0.2",
                            },
                            "actions": [],
                        }
                    }
                ]
            }
        }
        self.napp.check_switch_consistency(switch)
        mock_install_flows.assert_not_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_check_switch_flow_missing(self, *args):
        """Test check_switch_consistency method.

        This test checks the case when flow is missing.
        """
        (mock_flow_factory, mock_install_flows) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)

        flow_1 = MagicMock()
        flow_dict = {
            "flow": {
                "match": {
                    "in_port": 1,
                },
                "actions": [],
            }
        }
        flow_1.cookie = 0
        flow_1.as_dict.return_value = flow_dict

        serializer = MagicMock()
        serializer.from_dict.return_value = flow_1

        switch.flows = [flow_1]
        mock_flow_factory.return_value = serializer
        self.napp.stored_flows = {
            dpid: {
                84114904: [
                    {
                        "flow": {
                            "priority": 10,
                            "cookie": 84114904,
                            "match": {
                                "ipv4_src": "192.168.1.1",
                                "ipv4_dst": "192.168.0.2",
                            },
                            "actions": [],
                        }
                    }
                ]
            }
        }
        self.napp.check_switch_consistency(switch)
        mock_install_flows.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_check_switch_consistency_ignore(self, *args):
        """Test check_switch_consistency method.

        This test checks the case when a flow is missing in the last received
        flow_stats because the flow was just installed. Thus, it should be
        ignored.
        """
        (mock_flow_factory, mock_install_flows) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.flows = []

        flow_1 = MagicMock()
        flow_1.as_dict.return_value = {"flow_1": "data"}

        stored_flows = {
            0: [
                {
                    "created_at": now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "flow": {"flow_1": "data"},
                }
            ]
        }
        serializer = MagicMock()
        serializer.flow.cookie.return_value = 0

        mock_flow_factory.return_value = serializer
        self.napp.stored_flows = {dpid: stored_flows}
        self.napp.check_switch_consistency(switch)
        mock_install_flows.assert_not_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_check_storehouse_consistency(self, *args):
        """Test check_storehouse_consistency method.

        This test checks the case when a flow is missing in storehouse.
        """
        (mock_flow_factory, mock_install_flows) = args
        cookie_exception_interval = [(0x2B00000000000011, 0x2B000000000000FF)]
        self.napp.cookie_exception_range = cookie_exception_interval
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        flow_1 = MagicMock()
        flow_1.cookie = 0x2B00000000000010
        flow_1.as_dict.return_value = {"flow_1": "data", "cookie": 1}

        switch.flows = [flow_1]

        stored_flows = [{"flow": {"flow_2": "data", "cookie": 1}}]
        serializer = flow_1

        mock_flow_factory.return_value = serializer
        self.napp.stored_flows = {dpid: {0: stored_flows}}
        self.napp.check_storehouse_consistency(switch)
        mock_install_flows.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete_with_cookie(self, *args):
        """Test the non-strict matching method.

        A FlowMod with a non zero cookie but empty match fields shouldn't match
        other existing installed flows that have match clauses.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        stored_flow = {
            "flow": {
                "actions": [{"action_type": "output", "port": 4294967293}],
                "match": {"dl_vlan": 3799, "dl_type": 35020},
            },
        }
        flow_to_install = {
            "cookie": 6191162389751548793,
            "cookie_mask": 18446744073709551615,
        }
        stored_flows = {0: [stored_flow]}
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flows}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_not_called()
        self.assertDictEqual(self.napp.stored_flows[dpid][0][0], stored_flow)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete(self, *args):
        """Test the non-strict matching method.

        Test non-strict matching to delete a Flow using a cookie.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        stored_flow = {
            "flow": {
                "actions": [{"action_type": "set_vlan", "vlan_id": 300}],
                "cookie": 6191162389751548793,
                "match": {"dl_vlan": 300, "in_port": 1},
            },
        }
        stored_flow2 = {
            "flow": {
                "actions": [],
                "cookie": 4961162389751548787,
                "match": {"in_port": 2},
            },
        }
        flow_to_install = {
            "cookie": 6191162389751548793,
            "cookie_mask": 18446744073709551615,
        }
        stored_flows = {
            6191162389751548793: [stored_flow],
            4961162389751548787: [stored_flow2],
        }
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flows}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_called()
        self.assertEqual(len(self.napp.stored_flows), 1)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete_with_ipv4(self, *args):
        """Test the non-strict matching method.

        Test non-strict matching to delete a Flow using IPv4.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow_to_install = {"match": {"ipv4_src": "192.168.1.1"}}
        stored_flows = {
            84114904: [
                {
                    "flow": {
                        "priority": 10,
                        "cookie": 84114904,
                        "match": {
                            "ipv4_src": "192.168.1.1",
                            "ipv4_dst": "192.168.0.2",
                        },
                        "actions": [],
                    }
                }
            ],
            4961162389751548787: [
                {
                    "flow": {
                        "actions": [],
                        "cookie": 4961162389751548787,
                        "match": {"in_port": 2},
                    }
                }
            ],
        }
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flows}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_called()
        expected_stored = {
            4961162389751548787: [
                {
                    "flow": {
                        "actions": [],
                        "cookie": 4961162389751548787,
                        "match": {"in_port": 2},
                    },
                },
            ]
        }
        self.assertDictEqual(self.napp.stored_flows[dpid], expected_stored)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete_in_port(self, *args):
        """Test the non-strict matching method.

        Test non-strict matching to delete a Flow matching in_port.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow_to_install = {"match": {"in_port": 1}}
        stored_flow = {
            0: [
                {
                    "flow": {
                        "priority": 10,
                        "cookie": 84114904,
                        "match": {
                            "in_port": 1,
                            "dl_vlan": 100,
                        },
                        "actions": [],
                    },
                },
                {
                    "flow": {
                        "actions": [],
                        "match": {"in_port": 2},
                    },
                },
                {
                    "flow": {
                        "priority": 20,
                        "cookie": 84114904,
                        "match": {
                            "in_port": 1,
                            "dl_vlan": 102,
                        },
                        "actions": [],
                    },
                },
            ]
        }
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flow}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_called()

        expected_stored = {
            0: [
                {
                    "flow": {"actions": [], "match": {"in_port": 2}},
                }
            ]
        }
        self.assertDictEqual(self.napp.stored_flows[dpid], expected_stored)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete_all_if_empty_match(self, *args):
        """Test the non-strict matching method.

        Test non-strict matching to delete all if empty match is given.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow_to_install = {"match": {}}
        stored_flow = {
            0: [
                {
                    "flow": {
                        "priority": 10,
                        "match": {
                            "in_port": 1,
                            "dl_vlan": 100,
                        },
                        "actions": [],
                    }
                },
                {
                    "flow": {
                        "priority": 20,
                        "match": {
                            "in_port": 1,
                            "dl_vlan": 102,
                        },
                        "actions": [],
                    },
                },
            ]
        }
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flow}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_called()

        expected_stored = {}
        self.assertDictEqual(self.napp.stored_flows[dpid], expected_stored)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete_with_ipv4_fail(self, *args):
        """Test the non-strict matching method.

        Test non-strict Fail case matching to delete a Flow using IPv4.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        stored_flow = {
            "flow": {
                "priority": 10,
                "cookie": 84114904,
                "match": {
                    "ipv4_src": "192.168.2.1",
                    "ipv4_dst": "192.168.0.2",
                },
                "actions": [],
            },
        }
        stored_flow2 = {
            "flow": {
                "actions": [],
                "cookie": 4961162389751548787,
                "match": {"in_port": 2},
            },
        }
        flow_to_install = {"match": {"ipv4_src": "192.168.20.20"}}
        stored_flows = {0: [stored_flow, stored_flow2]}
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flows}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_not_called()
        expected_stored = {
            0: [
                {
                    "flow": {
                        "priority": 10,
                        "cookie": 84114904,
                        "match": {
                            "ipv4_src": "192.168.2.1",
                            "ipv4_dst": "192.168.0.2",
                        },
                        "actions": [],
                    },
                },
                {
                    "flow": {
                        "actions": [],
                        "cookie": 4961162389751548787,
                        "match": {"in_port": 2},
                    },
                },
            ]
        }
        self.assertDictEqual(self.napp.stored_flows[dpid], expected_stored)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    @patch("napps.kytos.flow_manager.main.StoreHouse.save_flow")
    def test_no_strict_delete_of10(self, *args):
        """Test the non-strict matching method.

        Test non-strict matching to delete a Flow using OF10.
        """
        (mock_save_flow, _, _) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x01)
        switch.id = dpid
        stored_flow = {
            "command": "add",
            "flow": {
                "actions": [{"max_len": 65535, "port": 6}],
                "cookie": 4961162389751548787,
                "match": {
                    "in_port": 80,
                    "dl_src": "00:00:00:00:00:00",
                    "dl_dst": "f2:0b:a4:7d:f8:ea",
                    "dl_vlan": 0,
                    "dl_vlan_pcp": 0,
                    "dl_type": 0,
                    "nw_tos": 0,
                    "nw_proto": 0,
                    "nw_src": "192.168.0.1",
                    "nw_dst": "0.0.0.0",
                    "tp_src": 0,
                    "tp_dst": 0,
                },
                "out_port": 65532,
                "priority": 123,
            },
        }
        stored_flow2 = {
            "command": "add",
            "flow": {
                "actions": [],
                "cookie": 4961162389751654,
                "match": {
                    "in_port": 2,
                    "dl_src": "00:00:00:00:00:00",
                    "dl_dst": "f2:0b:a4:7d:f8:ea",
                    "dl_vlan": 0,
                    "dl_vlan_pcp": 0,
                    "dl_type": 0,
                    "nw_tos": 0,
                    "nw_proto": 0,
                    "nw_src": "192.168.0.1",
                    "nw_dst": "0.0.0.0",
                    "tp_src": 0,
                    "tp_dst": 0,
                },
                "out_port": 655,
                "priority": 1,
            },
        }
        flow_to_install = {"match": {"in_port": 80, "wildcards": 4194303}}
        stored_flows = {0: [stored_flow, stored_flow2]}
        command = "delete"
        self.napp.stored_flows = {dpid: stored_flows}

        self.napp._store_changed_flows(command, flow_to_install, switch)
        mock_save_flow.assert_called()
        self.assertEqual(len(self.napp.stored_flows[dpid]), 0)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_consistency_cookie_ignored_range(self, *args):
        """Test the consistency `cookie` ignored range."""
        (_, mock_install_flows) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        cookie_ignored_interval = [
            (0x2B00000000000011, 0x2B000000000000FF),
            0x2B00000000000100,
        ]
        self.napp.cookie_ignored_range = cookie_ignored_interval
        flow = MagicMock()
        expected = [
            (0x2B00000000000010, 1),
            (0x2B00000000000013, 0),
            (0x2B00000000000100, 0),
            (0x2B00000000000101, 1),
        ]
        for cookie, called in expected:
            with self.subTest(cookie=cookie, called=called):
                mock_install_flows.call_count = 0
                flow.cookie = cookie
                flow.as_dict.return_value = {"flow_1": "data", "cookie": cookie}
                switch.flows = [flow]
                self.napp.stored_flows = {dpid: {0: [flow]}}
                self.napp.check_storehouse_consistency(switch)
                self.assertEqual(mock_install_flows.call_count, called)

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_consistency_table_id_ignored_range(self, *args):
        """Test the consistency `table_id` ignored range."""
        (_, mock_install_flows) = args
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        table_id_ignored_interval = [(1, 2), 3]
        self.napp.tab_id_ignored_range = table_id_ignored_interval

        flow = MagicMock()
        expected = [(0, 1), (3, 0), (4, 1)]
        for table_id, called in expected:
            with self.subTest(table_id=table_id, called=called):
                mock_install_flows.call_count = 0
                flow.table_id = table_id
                switch.flows = [flow]
                self.napp.stored_flows = {dpid: {0: [flow]}}
                self.napp.check_storehouse_consistency(switch)
                self.assertEqual(mock_install_flows.call_count, called)
