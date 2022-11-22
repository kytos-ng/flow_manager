"""Test Main methods."""
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from napps.kytos.flow_manager.exceptions import (
    InvalidCommandError,
    SwitchNotConnectedError,
)
from napps.kytos.of_core.v0x04.flow import Flow as Flow04
from pyof.v0x04.asynchronous.error_msg import ErrorType
from pyof.v0x04.controller2switch.flow_mod import FlowModCommand

from kytos.core.helpers import now
from kytos.lib.helpers import (
    get_connection_mock,
    get_controller_mock,
    get_kytos_event_mock,
    get_switch_mock,
    get_test_client,
)

# pylint: disable=too-many-lines,fixme,no-member
# TODO split this test suite in smaller ones


# pylint: disable=protected-access, too-many-public-methods
class TestMain(TestCase):
    """Tests for the Main class."""

    API_URL = "http://localhost:8181/api/kytos/flow_manager"

    def setUp(self):
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.kytos.flow_manager.main import Main

        Main.get_flow_controller = MagicMock()
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
        self.napp._consistency_verdict = 30

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

    def test_rest_list_stored_all_documents(self):
        """Test list_stored rest method."""
        flow_dict = {
            "switch": "00:00:00:00:00:00:00:01",
            "id": 1,
            "flow_id": 1,
            "state": "installed",
            "flow": {"priority": 10, "cookie": 84114964},
        }

        self.napp.flow_controller.find_flows.return_value = {
            "00:00:00:00:00:00:00:01": [flow_dict]
        }

        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/stored_flows"

        response = api.get(url)
        expected = [flow_dict]
        assert response.json["00:00:00:00:00:00:00:01"] == expected
        assert response.status_code == 200

    def test_rest_list_stored_by_state(self):
        """Test list_stored rest method."""
        flow_dict = {
            "switch": "00:00:00:00:00:00:00:01",
            "id": 1,
            "flow_id": 1,
            "state": "installed",
            "flow": {"priority": 10, "cookie": 84114964},
        }

        self.napp.flow_controller.find_flows.return_value = {
            "00:00:00:00:00:00:00:01": [flow_dict]
        }

        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/stored_flows?state=installed"

        response = api.get(url)
        for swith in response.json:
            assert response.json[swith][0]["state"] == "installed"
        assert response.status_code == 200

    def test_rest_list_stored_by_dpids(self):
        """Test list_stored rest method."""
        flow_dict = {
            "switch": "00:00:00:00:00:00:00:01",
            "id": 1,
            "flow_id": 1,
            "state": "installed",
            "flow": {"priority": 10, "cookie": 84114964},
        }

        self.napp.flow_controller.find_flows.return_value = {
            "00:00:00:00:00:00:00:01": [flow_dict]
        }

        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/stored_flows?dpid=00:00:00:00:00:00:00:01"

        response = api.get(url)
        for swith in response.json:
            assert swith == "00:00:00:00:00:00:00:01"
        assert response.status_code == 200

    def test_rest_list_stored_by_cookie(self):
        """Test list_stored rest method"""
        flow_dict = {
            "switch": "00:00:00:00:00:00:00:01",
            "id": 1,
            "flow_id": 1,
            "state": "installed",
            "flow": {"priority": 10, "cookie": "84114964"},
        }

        self.napp.flow_controller.find_flows.return_value = {
            "00:00:00:00:00:00:00:01": [flow_dict]
        }

        api = get_test_client(self.napp.controller, self.napp)
        url = (
            f"{self.API_URL}/v2/stored_flows?"
            "cookie_range=84114964&cookie_range=84114964"
        )

        response = api.get(url)
        for switch in response.json:
            assert switch == "00:00:00:00:00:00:00:01"
        assert response.status_code == 200

    def test_rest_list_stored_by_cookie_fail(self):
        """Test list_stored rest method failing with BadRequest"""
        api = get_test_client(self.napp.controller, self.napp)
        url = f"{self.API_URL}/v2/stored_flows?cookie_range=84114964"
        response = api.get(url)
        assert response.status_code == 400

        url = (
            f"{self.API_URL}/v2/stored_flows?cookie_range=84114964"
            "&cookie_range=84114964&cookie_range=84114964"
        )
        response = api.get(url)
        assert response.status_code == 400

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

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_rest_flow_mod_add_switch_not_connected(self, mock_install_flows):
        """Test sending a flow mod when a swith isn't connected."""
        api = get_test_client(self.napp.controller, self.napp)
        mock_install_flows.side_effect = SwitchNotConnectedError(
            "error", flow=MagicMock()
        )

        url = f"{self.API_URL}/v2/flows"
        response = api.post(url, json={"flows": [{"priority": 25}]})

        self.assertEqual(response.status_code, 424)

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    @patch("napps.kytos.flow_manager.main.Main._add_flow_mod_sent")
    @patch("napps.kytos.flow_manager.main.Main._send_barrier_request")
    @patch("napps.kytos.flow_manager.main.Main._send_flow_mod")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_rest_flow_mod_add_switch_not_connected_force(self, *args):
        """Test sending a flow mod when a swith isn't connected with force option."""
        (
            mock_flow_factory,
            mock_send_flow_mod,
            _,
            _,
            _,
        ) = args

        api = get_test_client(self.napp.controller, self.napp)
        mock_send_flow_mod.side_effect = SwitchNotConnectedError(
            "error", flow=MagicMock()
        )

        _id = str(uuid4())
        match_id = str(uuid4())
        serializer = MagicMock()
        flow = MagicMock()

        flow.id.return_value = _id
        flow.match_id = match_id
        serializer.from_dict.return_value = flow
        mock_flow_factory.return_value = serializer

        url = f"{self.API_URL}/v2/flows"
        flow_dict = {"flows": [{"priority": 25}]}
        response = api.post(url, json=dict(flow_dict, **{"force": True}))

        self.assertEqual(response.status_code, 202)

        flow_dicts = [
            {
                **{"flow": flow_dict["flows"][0]},
                **{"flow_id": flow.id, "switch": self.switch_01.id},
            }
        ]
        self.napp.flow_controller.upsert_flows.assert_called_with(
            [match_id],
            flow_dicts,
        )
        mock_flow_factory.assert_called_with(self.switch_01, Flow04)

    def test_get_all_switches_enabled(self):
        """Test _get_all_switches_enabled method."""
        switches = self.napp._get_all_switches_enabled()

        self.assertEqual(switches, [self.switch_01])

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    @patch("napps.kytos.flow_manager.main.Main._add_flow_mod_sent")
    @patch("napps.kytos.flow_manager.main.Main._send_barrier_request")
    @patch("napps.kytos.flow_manager.main.Main._send_flow_mod")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_install_flows(self, *args):
        """Test _install_flows method."""
        (
            mock_flow_factory,
            mock_send_flow_mod,
            mock_send_barrier_request,
            mock_add_flow_mod_sent,
            mock_send_napp_event,
        ) = args
        serializer = MagicMock()
        flow = MagicMock()
        flow_mod = MagicMock()
        flow_mod.command.value = FlowModCommand.OFPFC_ADD.value

        flow.as_of_add_flow_mod.return_value = flow_mod
        serializer.from_dict.return_value = flow
        mock_flow_factory.return_value = serializer

        flows_dict = {"flows": [MagicMock(), MagicMock()]}
        switches = [self.switch_01]
        self.napp._install_flows("add", flows_dict, switches)

        mock_send_flow_mod.assert_called_with(self.switch_01, flow_mod)
        assert mock_send_flow_mod.call_count == len(flows_dict["flows"])
        assert mock_send_barrier_request.call_count == 1
        mock_add_flow_mod_sent.assert_called_with(flow_mod.header.xid, flow, "add")
        mock_send_napp_event.assert_called_with(self.switch_01, flow, "pending")
        self.napp.flow_controller.upsert_flows.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    @patch("napps.kytos.flow_manager.main.Main._add_flow_mod_sent")
    @patch("napps.kytos.flow_manager.main.Main._send_barrier_request")
    @patch("napps.kytos.flow_manager.main.Main._send_flow_mod")
    @patch("napps.kytos.flow_manager.main.FlowFactory.get_class")
    def test_install_flows_with_delete_strict(self, *args):
        """Test _install_flows method with strict delete command."""
        (
            mock_flow_factory,
            mock_send_flow_mod,
            mock_send_barrier_request,
            mock_add_flow_mod_sent,
            mock_send_napp_event,
        ) = args
        serializer = MagicMock()
        flow = MagicMock()
        flow_mod = MagicMock()
        flow_mod.command.value = FlowModCommand.OFPFC_DELETE_STRICT.value

        flow.as_of_strict_delete_flow_mod.return_value = flow_mod
        serializer.from_dict.return_value = flow
        mock_flow_factory.return_value = serializer

        flows_dict = {"flows": [MagicMock()]}
        switches = [self.switch_01]
        self.napp._install_flows("delete_strict", flows_dict, switches)

        mock_send_flow_mod.assert_called_with(self.switch_01, flow_mod)
        mock_add_flow_mod_sent.assert_called_with(
            flow_mod.header.xid, flow, "delete_strict"
        )
        mock_send_napp_event.assert_called_with(self.switch_01, flow, "pending")
        mock_send_barrier_request.assert_called()
        self.napp.flow_controller.delete_flows_by_ids.assert_not_called()

    @patch("napps.kytos.flow_manager.main.log")
    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_event_add_flow(self, mock_install_flows, mock_log):
        """Test method for installing flows on the switches through events."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid)
        self.napp.controller.switches = {dpid: switch}
        mock_flow_dict = MagicMock()
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.install",
            content={"dpid": dpid, "flow_dict": mock_flow_dict},
        )
        self.napp.handle_flows_install_delete(event)
        mock_install_flows.assert_called_with(
            "add", mock_flow_dict, [switch], reraise_conn=True
        )
        mock_log.info.assert_called()

    @patch("napps.kytos.flow_manager.main.log")
    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_event_flows_install_delete(self, mock_install_flows, mock_log):
        """Test method for removing flows on the switches through events."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid)
        self.napp.controller.switches = {dpid: switch}
        mock_flow_dict = MagicMock()
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.delete",
            content={"dpid": dpid, "flow_dict": mock_flow_dict},
        )
        self.napp.handle_flows_install_delete(event)
        mock_install_flows.assert_called_with(
            "delete", mock_flow_dict, [switch], reraise_conn=True
        )
        mock_log.info.assert_called()

    @patch("napps.kytos.flow_manager.main.log")
    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_handle_flows_install_delete_fail(self, *args):
        """Test handle_flows_install_delete with failure scenarios."""
        (mock_send_napp_event, mock_install_flows, mock_log) = args
        dpid = "00:00:00:00:00:00:00:01"
        self.napp.controller.switches = {}
        mock_flow_dict = MagicMock()

        # 723, 746-751, 873
        # missing event args
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.delete",
            content={},
        )
        self.napp.handle_flows_install_delete(event)
        mock_log.error.assert_called()

        # invalid command
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.xpto",
            content={"dpid": dpid, "flow_dict": mock_flow_dict},
        )
        with self.assertRaises(ValueError):
            self.napp.handle_flows_install_delete(event)

        # install_flow exceptions
        event = get_kytos_event_mock(
            name="kytos.flow_manager.flows.install",
            content={"dpid": dpid, "flow_dict": mock_flow_dict},
        )
        mock_install_flows.side_effect = InvalidCommandError("error")
        mock_log.error.call_count = 0
        self.napp.handle_flows_install_delete(event)
        mock_log.error.assert_called()
        mock_install_flows.side_effect = SwitchNotConnectedError(
            "error", flow=MagicMock()
        )
        self.napp.handle_flows_install_delete(event)
        mock_send_napp_event.assert_called()

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
    def test_send_flow_mod_error(self, mock_buffers_put):
        """Test _send_flow_mod method error."""
        switch = get_switch_mock("00:00:00:00:00:00:00:01", 0x04)
        switch.is_connected = MagicMock(return_value=False)
        flow_mod = MagicMock()

        with self.assertRaises(SwitchNotConnectedError):
            self.napp._send_flow_mod(switch, flow_mod)

        mock_buffers_put.assert_not_called()

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
        flow.id = "1"
        flow.as_dict.return_value = {}
        flow.cookie = 0
        self.napp._flow_mods_sent[0] = (flow, "add")

        switch = get_switch_mock("00:00:00:00:00:00:00:01")
        switch.connection = get_connection_mock(
            0x04, get_switch_mock("00:00:00:00:00:00:00:01")
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
        self.napp.flow_controller.delete_flow_by_id.assert_called_with(flow.id)

    def test_handle_errors_ofpet_hello_failed(self):
        """Test handle_errors ofpet_hello_failed."""
        content = MagicMock()
        event = MagicMock(content=dict(message=content))
        content.error_type = ErrorType.OFPET_HELLO_FAILED
        content.code = 5
        self.napp.handle_errors(event)
        content.data.pack.assert_not_called()

    @patch("napps.kytos.flow_manager.main.ENABLE_CONSISTENCY_CHECK", False)
    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_resend_stored_flows(self, mock_install_flows):
        """Test resend stored flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        mock_event = MagicMock()
        self.napp.flow_controller.get_flows.return_value = [MagicMock()]

        mock_event.content = {"switch": switch}
        self.napp.controller.switches = {dpid: switch}
        self.napp.resend_stored_flows(mock_event)
        mock_install_flows.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_check_switch_flow_missing(self, mock_install_flows):
        """Test check_missing_flows method.

        This test checks the case when flow is missing.
        """
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        flow_1 = MagicMock(id="1", match_id="2")
        switch.flows = [flow_1]
        self.napp.flow_controller.get_flows_lte_updated_at.return_value = [
            {"flow_id": "2", "flow": {}}
        ]
        self.napp.check_missing_flows(switch)
        mock_install_flows.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_check_alien_flows(self, mock_install_flows):
        """Test check_alien_flows method.

        This test checks the case when a flow is missing in the switch.
        """
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        flow_1 = MagicMock(id="1", match_id="3")
        switch.flows = [flow_1]
        self.napp.flow_controller.get_flows.return_value = [
            {
                "flow_id": "2",
                "id": "3",
                "flow": {},
                "updated_at": datetime.utcnow()
                - timedelta(seconds=self.napp._consistency_verdict),
            }
        ]
        self.napp.check_alien_flows(switch)
        mock_install_flows.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_check_alien_flows_skip_recent_overwrite(self, mock_install_flows):
        """Test check_alien_flows skipped method.

        This test checks the case when an alien recent overwrite should be skipped
        """
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        flow_1 = MagicMock(id="1", match_id="3")
        switch.flows = [flow_1]

        verdict_dt = datetime.utcnow() - timedelta(
            seconds=self.napp._consistency_verdict
        )
        # different flow_id, but same match_id and recent updated
        self.napp.flow_controller.get_flows.return_value = [
            {
                "flow_id": "2",
                "id": "3",
                "flow": {},
                "updated_at": datetime.utcnow()
                - timedelta(seconds=self.napp._consistency_verdict - 5),
            }
        ]
        self.napp.check_alien_flows(switch, verdict_dt)
        mock_install_flows.assert_not_called()

    @patch("napps.kytos.flow_manager.main.Main._install_flows")
    def test_check_alien_flows_skip_recent_delete(self, mock_install_flows):
        """Test check_alien_flows skipped method.

        This test checks the case when an alien recent delete should be skipped
        """
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        flow_1 = MagicMock(id="1", match_id="3")
        switch.flows = [flow_1]

        response = [
            {
                "flow_id": "2",
                "id": "3",
                "state": "installed",
                "flow": {},
                "updated_at": datetime.utcnow()
                - timedelta(seconds=self.napp._consistency_verdict),
            }
        ]
        self.napp.flow_controller.get_flows.return_value = response

        response[0]["state"] = "deleted"
        response[0]["flow_id"] = "1"
        self.napp.flow_controller.get_flows_by_state.return_value = response

        self.napp.check_alien_flows(switch)
        mock_install_flows.assert_not_called()

    def test_consistency_cookie_ignored_range(self):
        """Test the consistency `cookie` ignored range."""
        cookie_ignored_interval = [
            (0x2B00000000000011, 0x2B000000000000FF),
            0x2B00000000000100,
        ]
        self.napp.cookie_ignored_range = cookie_ignored_interval
        flow = MagicMock()
        expected = [
            (0x2B00000000000010, True),
            (0x2B00000000000013, False),
            (0x2B00000000000100, False),
            (0x2B00000000000101, True),
        ]
        for cookie, is_not_ignored in expected:
            with self.subTest(cookie=cookie, is_not_ignored=is_not_ignored):
                flow.cookie = cookie
                flow.table_id = 0
                assert self.napp.is_not_ignored_flow(flow) == is_not_ignored

    def test_consistency_table_id_ignored_range(self):
        """Test the consistency `table_id` ignored range."""
        table_id_ignored_interval = [(1, 2), 3]
        self.napp.tab_id_ignored_range = table_id_ignored_interval

        flow = MagicMock()
        expected = [(0, True), (3, False), (4, True)]
        for table_id, is_not_ignored in expected:
            with self.subTest(table_id=table_id, is_not_ignored=is_not_ignored):
                flow.cookie = 0
                flow.table_id = table_id
                assert self.napp.is_not_ignored_flow(flow) == is_not_ignored

    def test_check_consistency(self):
        """Test check_consistency."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        switch.flows = []
        self.napp.flow_controller.get_flow_check.return_value = None
        self.napp.check_missing_flows = MagicMock()
        self.napp.check_alien_flows = MagicMock()
        self.napp.check_consistency(switch)
        self.napp.flow_controller.upsert_flow_check.assert_called_with(switch.id)
        self.napp.check_missing_flows.assert_called_with(switch, None)
        self.napp.check_alien_flows.assert_called_with(switch, None)

    def test_check_consistency_flow_check_exists(self):
        """Test check_consistency when flow_check exists, this is the case
        when a consistency check has run before."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        switch.flows = []
        dtnow = datetime.utcnow() - timedelta(seconds=self.napp._consistency_verdict)
        self.napp.flow_controller.get_flow_check.return_value = {"updated_at": dtnow}
        self.napp.check_missing_flows = MagicMock()
        self.napp.check_alien_flows = MagicMock()
        self.napp.check_consistency(switch)
        self.napp.flow_controller.upsert_flow_check.assert_called_with(switch.id)
        check_missing_flows = self.napp.check_missing_flows
        check_missing_flows.assert_called()
        assert check_missing_flows.call_args[0][0] == switch
        assert check_missing_flows.call_args[0][1] <= dtnow + timedelta(seconds=5)
        check_alien_flows = self.napp.check_alien_flows
        check_alien_flows.assert_called()
        assert check_alien_flows.call_args[0][0] == switch
        assert check_alien_flows.call_args[0][1] <= dtnow + timedelta(seconds=5)

    def test_reset_flow_check(self):
        """Test reset_flow_Check."""
        dpid = "00:00:00:00:00:00:00:01"
        self.napp.reset_flow_check(dpid)
        self.napp.flow_controller.upsert_flow_check.assert_called_with(
            dpid, state="inactive"
        )

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_on_ofpt_flow_removed(self, mock_send_napp_event):
        """Test on_ofpt_flow_removed."""
        mock = MagicMock()
        mock.source.switch = "switch"
        mock.message = {}
        self.napp._on_ofpt_flow_removed(mock)
        mock_send_napp_event.assert_called_with("switch", {}, "delete")

    def test_delete_matched_flows(self):
        """Test delete_matched_flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow1 = MagicMock(id="1", match_id="2")
        flow1_dict = {
            "_id": flow1.match_id,
            "id": flow1.match_id,
            "flow_id": flow1.id,
            "match_id": flow1.match_id,
            "flow": {"match": {"in_port": 1}},
        }
        flow1.__getitem__.side_effect = flow1_dict.__getitem__
        flows = [flow1]
        switch.flows = flows
        self.napp.flow_controller.get_flows_by_cookies.return_value = {
            switch.id: [flow1_dict]
        }
        self.napp.delete_matched_flows([flow1_dict], {switch.id: switch})

        assert self.napp.flow_controller.upsert_flows.call_count == 1
        call_args = self.napp.flow_controller.upsert_flows.call_args
        assert list(call_args[0][0]) == [flow1.match_id]

        # second arg should be the same dict values, except with state deleted
        expected = dict(flow1_dict)
        assert expected["state"] == "deleted"
        assert list(call_args[0][1])[0] == expected

    def test_delete_matched_flows_connection_none(self):
        """Test delete_matched_flows connection none."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        # To simulate a coner case when a handshake hasn't been completed
        switch.connection = None
        switch.id = dpid
        flow1 = MagicMock(id="1", match_id="2")
        flow1_dict = {
            "_id": flow1.match_id,
            "id": flow1.match_id,
            "flow_id": flow1.id,
            "match_id": flow1.match_id,
            "flow": {"match": {"in_port": 1}},
        }
        flow1.__getitem__.side_effect = flow1_dict.__getitem__
        flows = [flow1]
        switch.flows = flows
        self.napp.flow_controller.get_flows_by_cookies.return_value = {
            switch.id: [flow1_dict]
        }
        self.napp.delete_matched_flows([flow1_dict], {switch.id: switch})

        assert self.napp.flow_controller.upsert_flows.call_count == 1
        call_args = self.napp.flow_controller.upsert_flows.call_args
        assert list(call_args[0][0]) == [flow1.match_id]

        # second arg should be the same dict values, except with state deleted
        expected = dict(flow1_dict)
        assert expected["state"] == "deleted"
        assert list(call_args[0][1])[0] == expected

    def test_add_barrier_request(self):
        """Test add barrier request."""
        dpid = "00:00:00:00:00:00:00:01"
        barrier_xid = 1
        flow_mods_xids = [2]
        flow_mods = [MagicMock(header=MagicMock(xid=xid)) for xid in flow_mods_xids]
        assert barrier_xid not in self.napp._pending_barrier_reply[dpid]
        self.napp._add_barrier_request(dpid, barrier_xid, flow_mods)
        assert self.napp._pending_barrier_reply[dpid][barrier_xid] == flow_mods_xids

    def test_add_barrier_request_max_size_fifo(self):
        """Test add barrier request max size fifo popitem."""
        dpid = "00:00:00:00:00:00:00:01"
        max_size = 3
        barrier_xid_offset = 0
        flow_xid_offset = 1000
        overflow = 1

        self.napp._pending_barrier_max_size = max_size
        assert len(self.napp._pending_barrier_reply[dpid]) == 0

        for i in range(max_size + overflow):
            self.napp._add_barrier_request(
                dpid,
                barrier_xid_offset + i,
                [MagicMock(header=MagicMock(xid=flow_xid_offset + i))],
            )
        assert len(self.napp._pending_barrier_reply[dpid]) == max_size

        for i in range(overflow, max_size + overflow):
            assert i in self.napp._pending_barrier_reply[dpid]

        for i in range(overflow):
            assert i not in self.napp._pending_barrier_reply[dpid]

    def test_send_barrier_request(self):
        """Test send barrier request."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid

        flow_mods_xids = [123]
        flow_mods = [MagicMock(header=MagicMock(xid=xid)) for xid in flow_mods_xids]

        self.napp._send_barrier_request(switch, flow_mods)
        assert (
            list(self.napp._pending_barrier_reply[switch.id].values())[-1]
            == flow_mods_xids
        )

    @patch("napps.kytos.flow_manager.main.Main._publish_installed_flow")
    def test_on_ofpt_barrier_reply(self, mock_publish):
        """Test on_ofpt barrier reply."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid

        flow_mods_xids = [123]
        flow_mods = [MagicMock(header=MagicMock(xid=xid)) for xid in flow_mods_xids]

        self.napp._send_barrier_request(switch, flow_mods)
        assert (
            list(self.napp._pending_barrier_reply[switch.id].values())[-1]
            == flow_mods_xids
        )

        barrier_xid = list(self.napp._pending_barrier_reply[switch.id].keys())[-1]
        for flow_mod in flow_mods:
            self.napp._add_flow_mod_sent(flow_mod.header.xid, flow_mod, "add")

        event = MagicMock()
        event.message.header.xid = barrier_xid
        assert barrier_xid
        assert (
            self.napp._pending_barrier_reply[switch.id][barrier_xid] == flow_mods_xids
        )
        event.source.switch = switch

        self.napp._on_ofpt_barrier_reply(event)
        mock_publish.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_on_openflow_connection_error(self, mock_send_napp_event):
        """Test on_openflow_connection_error."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid

        mock = MagicMock()
        mock.event.content = {"destination": switch}
        self.napp._send_openflow_connection_error(mock)
        mock_send_napp_event.assert_called()

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_publish_installed_flows(self, mock_send_napp_event):
        """Test publish_installed_flows."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow1, flow2 = MagicMock(id="1"), MagicMock(id="2")
        flow1_dict, flow2_dict = {"_id": flow1.id}, {"_id": flow2.id}
        flow1.__getitem__.side_effect, flow2.__getitem__.side_effect = (
            flow1_dict.__getitem__,
            flow2_dict.__getitem__,
        )
        flows = [flow1, flow2]
        switch.flows = flows
        self.napp.flow_controller.get_flows_by_state.return_value = flows
        self.napp.publish_installed_flows(switch)
        assert mock_send_napp_event.call_count == len(flows)
        assert self.napp.flow_controller.update_flows_state.call_count == 1

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_publish_installed_flow(self, mock_send_napp_event):
        """Test publish_installed_flow."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flows = [MagicMock(id="1")]
        self.napp._publish_installed_flow(switch, flows)
        mock_send_napp_event.assert_called()
        self.napp.flow_controller.update_flows_state.assert_called_with(
            [flow.id for flow in flows], "installed"
        )

    @patch("napps.kytos.flow_manager.main.Main._send_barrier_request")
    def test_retry_on_openflow_connection_error(self, mock_barrier):
        """Test retry on openflow connection error."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid

        flow = MagicMock()
        flow.as_dict.return_value = {}
        flow.xid = 1
        self.napp._flow_mods_sent[flow.xid] = (flow, "add")

        mock_ev = MagicMock()
        mock_ev.event.content = {"destination": switch}
        min_wait = 0.2
        multiplier = 2
        assert self.napp._retry_on_openflow_connection_error(
            mock_ev,
            max_retries=3,
            min_wait=min_wait,
            multiplier=multiplier,
            send_barrier=True,
        )
        (count, _, wait_acc) = self.napp._flow_mods_retry_count[flow.xid]
        assert count == 1
        assert wait_acc == min_wait * multiplier
        assert mock_barrier.call_count == 1

    @patch("napps.kytos.flow_manager.main.Main._send_openflow_connection_error")
    def test_retry_on_openflow_connection_error_send_event(self, mock_send):
        """Test retry on openflow connection error send event."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid

        flow = MagicMock()
        flow.as_dict.return_value = {}
        flow.xid = 1
        self.napp._flow_mods_sent[flow.xid] = (flow, "add")

        # make sure a previous retry has stored executed
        self.napp._flow_mods_retry_count[flow.xid] = (3, now(), 10)

        mock_ev = MagicMock()
        mock_ev.event.content = {"destination": switch}
        min_wait = 0.2
        assert not self.napp._retry_on_openflow_connection_error(
            mock_ev,
            max_retries=3,
            min_wait=min_wait,
            multiplier=2,
            send_barrier=True,
        )
        assert mock_send.call_count == 1

    def test_retry_on_openflow_connection_error_early_return(self):
        """Test retry on openflow connection error early returns."""
        max_retries = 0
        min_wait = 0.2
        multiplier = 2
        with self.assertRaises(ValueError) as exc:
            self.napp._retry_on_openflow_connection_error(
                {}, max_retries, min_wait, multiplier
            )
        assert "should be > 0" in str(exc.exception)

        self.napp._flow_mods_sent = {}
        mock = MagicMock()
        with self.assertRaises(ValueError) as exc:
            self.napp._retry_on_openflow_connection_error(
                mock, max_retries + 1, min_wait, multiplier
            )
        assert "not found on flow mods sent" in str(exc.exception)

    @patch("napps.kytos.flow_manager.main.Main._send_napp_event")
    def test_send_openflow_connection_error(self, mock_send):
        """Test _send_openflow_connection_error."""
        dpid = "00:00:00:00:00:00:00:01"
        switch = get_switch_mock(dpid, 0x04)
        switch.id = dpid
        flow = MagicMock()
        flow.as_dict.return_value = {}
        flow.xid = 1
        self.napp._flow_mods_sent[flow.xid] = (flow, "add")

        mock_ev = MagicMock()
        mock_ev.event.content = {"destination": switch}
        self.napp._send_openflow_connection_error(mock_ev)
        assert mock_send.call_count == 1
