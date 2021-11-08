"""kytos/flow_manager NApp installs, lists and deletes switch flows."""

# pylint: disable=relative-beyond-top-level
import itertools
from collections import OrderedDict, defaultdict
from copy import deepcopy
from threading import Lock

from flask import jsonify, request
from napps.kytos.flow_manager.match import match_flow
from napps.kytos.flow_manager.storehouse import StoreHouse
from napps.kytos.of_core.flow import FlowFactory
from napps.kytos.of_core.settings import STATS_INTERVAL
from pyof.foundation.base import UBIntBase
from pyof.v0x01.asynchronous.error_msg import BadActionCode
from pyof.v0x01.common.phy_port import PortConfig
from werkzeug.exceptions import BadRequest, NotFound, UnsupportedMediaType

from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import get_time, listen_to, now

from .exceptions import InvalidCommandError
from .settings import (
    CONSISTENCY_COOKIE_IGNORED_RANGE,
    CONSISTENCY_TABLE_ID_IGNORED_RANGE,
    ENABLE_CONSISTENCY_CHECK,
    FLOWS_DICT_MAX_SIZE,
)


def cast_fields(flow_dict):
    """Make casting the match fields from UBInt() to native int ."""
    match = flow_dict["match"]
    for field, value in match.items():
        if isinstance(value, UBIntBase):
            match[field] = int(value)
    flow_dict["match"] = match
    return flow_dict


def _validate_range(values):
    """Check that the range of flows ignored by the consistency is valid."""
    if len(values) != 2:
        msg = f"The tuple must have 2 items, not {len(values)}"
        raise ValueError(msg)
    first, second = values
    if second < first:
        msg = f"The first value is bigger than the second: {values}"
        raise ValueError(msg)
    if not isinstance(first, int) or not isinstance(second, int):
        msg = f"Expected a tuple of integers, received {values}"
        raise TypeError(msg)


def _valid_consistency_ignored(consistency_ignored_list):
    """Check the format of the list of ignored consistency flows.

    Check that the list of ignored flows in the consistency check
    is well formatted. Returns True, if the list is well
    formatted, otherwise return False.
    """
    msg = (
        "The list of ignored flows in the consistency check"
        "is not well formatted, it will be ignored: %s"
    )
    for consistency_ignored in consistency_ignored_list:
        if isinstance(consistency_ignored, tuple):
            try:
                _validate_range(consistency_ignored)
            except (TypeError, ValueError) as error:
                log.warn(msg, error)
                return False
        elif not isinstance(consistency_ignored, (int, tuple)):
            error_msg = (
                "The elements must be of class int or tuple"
                f" but they are: {type(consistency_ignored)}"
            )
            log.warn(msg, error_msg)
            return False
    return True


class Main(KytosNApp):
    """Main class to be used by Kytos controller."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        log.debug("flow-manager starting")
        self._flow_mods_sent = OrderedDict()
        self._flow_mods_sent_max_size = FLOWS_DICT_MAX_SIZE
        self.cookie_ignored_range = []
        self.tab_id_ignored_range = []
        if _valid_consistency_ignored(CONSISTENCY_COOKIE_IGNORED_RANGE):
            self.cookie_ignored_range = CONSISTENCY_COOKIE_IGNORED_RANGE
        if _valid_consistency_ignored(CONSISTENCY_TABLE_ID_IGNORED_RANGE):
            self.tab_id_ignored_range = CONSISTENCY_TABLE_ID_IGNORED_RANGE

        # Storehouse client to save and restore flow data:
        self.storehouse = StoreHouse(self.controller)

        self._storehouse_lock = Lock()

        # Format of stored flow data:
        # {'flow_persistence': {'dpid_str': {cookie_val: [
        #                                     {'flow': {flow_dict}}]}}}
        self.stored_flows = {}
        self.resent_flows = set()

    def execute(self):
        """Run once on NApp 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        self._load_flows()

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    def stored_flows_list(self, dpid):
        """Ordered list of all stored flows given a dpid."""
        return itertools.chain(*list(self.stored_flows[dpid].values()))

    @listen_to("kytos/of_core.handshake.completed")
    def resend_stored_flows(self, event):
        """Resend stored Flows."""
        # if consistency check is enabled, it should take care of this
        if ENABLE_CONSISTENCY_CHECK:
            return
        switch = event.content["switch"]
        dpid = str(switch.dpid)
        # This can be a problem because this code is running a thread
        if dpid in self.resent_flows:
            log.debug(f"Flow already resent to the switch {dpid}")
            return
        if dpid in self.stored_flows:
            for flow in self.stored_flows_list(dpid):
                flows_dict = {"flows": [flow["flow"]]}
                self._install_flows("add", flows_dict, [switch])
            self.resent_flows.add(dpid)
            log.info(f"Flows resent to Switch {dpid}")

    @staticmethod
    def is_ignored(field, ignored_range):
        """Check that the flow field is in the range of ignored flows.

        Returns True, if the field is in the range of ignored flows,
        otherwise it returns False.
        """
        for i in ignored_range:
            if isinstance(i, tuple):
                start_range, end_range = i
                if start_range <= field <= end_range:
                    return True
            if isinstance(i, int):
                if field == i:
                    return True
        return False

    @listen_to("kytos/of_core.flow_stats.received")
    def on_flow_stats_check_consistency(self, event):
        """Check the consistency of a switch upon receiving flow stats."""
        self.check_consistency(event.content["switch"])

    def check_consistency(self, switch):
        """Check consistency of stored and installed flows given a switch."""
        if not ENABLE_CONSISTENCY_CHECK or not switch.is_enabled():
            return
        with self._storehouse_lock:
            log.debug(f"check_consistency on switch {switch.id} has started")
            self.check_storehouse_consistency(switch)
            if switch.dpid in self.stored_flows:
                self.check_switch_consistency(switch)
            log.debug(f"check_consistency on switch {switch.id} is done")

    @staticmethod
    def switch_flows_by_cookie(switch):
        """Build switch.flows indexed by cookie."""
        installed_flows = defaultdict(list)
        for cookie, flows in itertools.groupby(switch.flows, lambda x: x.cookie):
            for flow in flows:
                installed_flows[cookie].append(flow)
        return installed_flows

    def check_switch_consistency(self, switch):
        """Check consistency of stored flows for a specific switch."""
        dpid = switch.dpid
        serializer = FlowFactory.get_class(switch)
        installed_flows = self.switch_flows_by_cookie(switch)

        for cookie, stored_flows in self.stored_flows[dpid].items():
            for stored_flow in stored_flows:
                stored_time = get_time(
                    stored_flow.get("created_at", "0001-01-01T00:00:00")
                )
                if (now() - stored_time).seconds <= STATS_INTERVAL:
                    continue
                stored_flow_obj = serializer.from_dict(stored_flow["flow"], switch)
                if stored_flow_obj in installed_flows[cookie]:
                    continue

                log.info(f"Consistency check: missing flow on switch {dpid}.")
                flow = {"flows": [stored_flow["flow"]]}
                self._install_flows("add", flow, [switch], save=False)
                log.info(
                    f"Flow forwarded to switch {dpid} to be installed. Flow: {flow}"
                )

    def check_storehouse_consistency(self, switch):
        """Check consistency of installed flows for a specific switch."""
        dpid = switch.dpid

        for cookie, flows in self.switch_flows_by_cookie(switch).items():
            if self.is_ignored(cookie, self.cookie_ignored_range):
                continue

            serializer = FlowFactory.get_class(switch)
            stored_flows_list = [
                serializer.from_dict(stored_flow["flow"], switch)
                for stored_flow in self.stored_flows[dpid].get(cookie, [])
            ]
            log.debug(
                f"stored_flows_list on switch {switch.id} by cookie: {hex(cookie)}: "
                f"{self.stored_flows[dpid].get(cookie, [])}"
            )

            for installed_flow in flows:
                if self.is_ignored(installed_flow.table_id, self.tab_id_ignored_range):
                    continue

                if dpid not in self.stored_flows:
                    log.info(
                        f"Consistency check: alien flow on switch {dpid}, dpid"
                        " not indexed"
                    )
                    flow = {"flows": [installed_flow.as_dict()]}
                    command = "delete_strict"
                    self._install_flows(command, flow, [switch], save=False)
                    log.info(
                        f"Flow forwarded to switch {dpid} to be deleted. Flow: {flow}"
                    )
                    continue

                if installed_flow not in stored_flows_list:
                    log.info(f"Consistency check: alien flow on switch {dpid}")
                    flow = {"flows": [installed_flow.as_dict()]}
                    command = "delete_strict"
                    self._install_flows(command, flow, [switch], save=False)
                    log.info(
                        f"Flow forwarded to switch {dpid} to be deleted. Flow: {flow}"
                    )

    # pylint: disable=attribute-defined-outside-init
    def _load_flows(self):
        """Load stored flows."""
        try:
            data = self.storehouse.get_data()["flow_persistence"]
            if "id" in data:
                del data["id"]
            self.stored_flows = data
        except (KeyError, FileNotFoundError) as error:
            log.debug(f"There are no flows to load: {error}")
        else:
            log.info("Flows loaded.")

    def _del_matched_flows_store(self, flow_dict, switch):
        """Try to delete matching stored flows given a flow dict."""
        stored_flows_box = deepcopy(self.stored_flows)

        if switch.id not in stored_flows_box:
            return

        cookies = (
            self.stored_flows[switch.id].keys()
            if flow_dict.get("cookie") is None
            else [int(flow_dict.get("cookie", 0))]
        )

        has_deleted_any_flow = False
        for cookie in cookies:
            stored_flows = stored_flows_box[switch.id].get(cookie, [])
            if not stored_flows:
                continue

            deleted_flows_idxs = set()
            for i, stored_flow in enumerate(stored_flows):
                version = switch.connection.protocol.version
                # No strict match
                if match_flow(flow_dict, version, stored_flow["flow"]):
                    deleted_flows_idxs.add(i)

            if not deleted_flows_idxs:
                continue

            stored_flows = [
                flow
                for i, flow in enumerate(stored_flows)
                if i not in deleted_flows_idxs
            ]
            has_deleted_any_flow = True

            if stored_flows:
                stored_flows_box[switch.id][cookie] = stored_flows
            else:
                stored_flows_box[switch.id].pop(cookie, None)

        if has_deleted_any_flow:
            stored_flows_box["id"] = "flow_persistence"
            self.storehouse.save_flow(stored_flows_box)
            del stored_flows_box["id"]
            self.stored_flows = deepcopy(stored_flows_box)

    # pylint: disable=fixme
    def _add_flow_store(self, flow_dict, switch):
        """Try to add a flow dict in the store."""
        installed_flow = {}
        installed_flow["flow"] = flow_dict
        installed_flow["created_at"] = now().strftime("%Y-%m-%dT%H:%M:%S")

        stored_flows_box = deepcopy(self.stored_flows)
        cookie = int(flow_dict.get("cookie", 0))
        if switch.id not in stored_flows_box:
            stored_flows_box[switch.id] = OrderedDict()

        # TODO handle issue 23 (overlapping FlowMod add)
        if not stored_flows_box[switch.id].get(cookie):
            stored_flows_box[switch.id][cookie] = [installed_flow]
        else:
            stored_flows_box[switch.id][cookie].append(installed_flow)

        stored_flows_box["id"] = "flow_persistence"
        self.storehouse.save_flow(stored_flows_box)
        del stored_flows_box["id"]
        self.stored_flows = deepcopy(stored_flows_box)

    def _store_changed_flows(self, command, flow_dict, switch):
        """Store changed flows.

        Args:
            command: Flow command to be installed
            flow: flow dict to be stored
            switch: Switch target
        """
        cmd_handlers = {
            "add": self._add_flow_store,
            "delete": self._del_matched_flows_store,
        }
        if command not in cmd_handlers:
            raise ValueError(
                f"Invalid command: {command}, supported: {list(cmd_handlers.keys())}"
            )
        return cmd_handlers[command](flow_dict, switch)

    @rest("v2/flows")
    @rest("v2/flows/<dpid>")
    def list(self, dpid=None):
        """Retrieve all flows from a switch identified by dpid.

        If no dpid is specified, return all flows from all switches.
        """
        if dpid is None:
            switches = self.controller.switches.values()
        else:
            switches = [self.controller.get_switch_by_dpid(dpid)]

            if not any(switches):
                raise NotFound("Switch not found")

        switch_flows = {}

        for switch in switches:
            flows_dict = [cast_fields(flow.as_dict()) for flow in switch.flows]
            switch_flows[switch.dpid] = {"flows": flows_dict}

        return jsonify(switch_flows)

    @listen_to("kytos.flow_manager.flows.(install|delete)")
    def event_flows_install_delete(self, event):
        """Install or delete flows in the switches through events.

        Install or delete Flow of switches identified by dpid.
        """
        try:
            dpid = event.content["dpid"]
            flow_dict = event.content["flow_dict"]
        except KeyError as error:
            log.error("Error getting fields to install or remove " f"Flows: {error}")
            return

        if event.name == "kytos.flow_manager.flows.install":
            command = "add"
        elif event.name == "kytos.flow_manager.flows.delete":
            command = "delete"
        else:
            msg = f'Invalid event "{event.name}", should be install|delete'
            raise ValueError(msg)

        switch = self.controller.get_switch_by_dpid(dpid)
        try:
            self._install_flows(command, flow_dict, [switch])
        except InvalidCommandError as error:
            log.error(
                "Error installing or deleting Flow through" f" Kytos Event: {error}"
            )

    @rest("v2/flows", methods=["POST"])
    @rest("v2/flows/<dpid>", methods=["POST"])
    def add(self, dpid=None):
        """Install new flows in the switch identified by dpid.

        If no dpid is specified, install flows in all switches.
        """
        return self._send_flow_mods_from_request(dpid, "add")

    @rest("v2/delete", methods=["POST"])
    @rest("v2/delete/<dpid>", methods=["POST"])
    @rest("v2/flows", methods=["DELETE"])
    @rest("v2/flows/<dpid>", methods=["DELETE"])
    def delete(self, dpid=None):
        """Delete existing flows in the switch identified by dpid.

        If no dpid is specified, delete flows from all switches.
        """
        return self._send_flow_mods_from_request(dpid, "delete")

    def _get_all_switches_enabled(self):
        """Get a list of all switches enabled."""
        switches = self.controller.switches.values()
        return [switch for switch in switches if switch.is_enabled()]

    def _send_flow_mods_from_request(self, dpid, command, flows_dict=None):
        """Install FlowsMods from request."""
        if flows_dict is None:
            flows_dict = request.get_json() or {}
            content_type = request.content_type
            # Get flow to check if the request is well-formed
            flows = flows_dict.get("flows", [])

            if content_type is None:
                result = "The request body is empty"
                raise BadRequest(result)

            if content_type != "application/json":
                result = (
                    "The content type must be application/json "
                    f"(received {content_type})."
                )
                raise UnsupportedMediaType(result)

            if not any(flows_dict) or not any(flows):
                result = "The request body is not well-formed."
                raise BadRequest(result)

        log.info(
            f"Send FlowMod from request dpid: {dpid} command: {command}"
            f" flows_dict: {flows_dict}"
        )
        if dpid:
            switch = self.controller.get_switch_by_dpid(dpid)
            if not switch:
                return jsonify({"response": "dpid not found."}), 404
            elif switch.is_enabled() is False:
                if command == "delete":
                    self._install_flows(command, flows_dict, [switch])
                else:
                    return jsonify({"response": "switch is disabled."}), 404
            else:
                self._install_flows(command, flows_dict, [switch])
        else:
            self._install_flows(command, flows_dict, self._get_all_switches_enabled())

        return jsonify({"response": "FlowMod Messages Sent"}), 202

    def _install_flows(self, command, flows_dict, switches=[], save=True):
        """Execute all procedures to install flows in the switches.

        Args:
            command: Flow command to be installed
            flows_dict: Dictionary with flows to be installed in the switches.
            switches: A list of switches
            save: A boolean to save flows in the storehouse (True) or not
        """
        for switch in switches:
            serializer = FlowFactory.get_class(switch)
            flows = flows_dict.get("flows", [])
            for flow_dict in flows:
                flow = serializer.from_dict(flow_dict, switch)
                if command == "delete":
                    flow_mod = flow.as_of_delete_flow_mod()
                elif command == "delete_strict":
                    flow_mod = flow.as_of_strict_delete_flow_mod()
                elif command == "add":
                    flow_mod = flow.as_of_add_flow_mod()
                else:
                    raise InvalidCommandError
                self._send_flow_mod(flow.switch, flow_mod)
                self._add_flow_mod_sent(flow_mod.header.xid, flow, command)

                self._send_napp_event(switch, flow, command)
                if save:
                    with self._storehouse_lock:
                        self._store_changed_flows(command, flow_dict, switch)

    def _add_flow_mod_sent(self, xid, flow, command):
        """Add the flow mod to the list of flow mods sent."""
        if len(self._flow_mods_sent) >= self._flow_mods_sent_max_size:
            self._flow_mods_sent.popitem(last=False)
        self._flow_mods_sent[xid] = (flow, command)

    def _send_flow_mod(self, switch, flow_mod):
        event_name = "kytos/flow_manager.messages.out.ofpt_flow_mod"

        content = {"destination": switch.connection, "message": flow_mod}

        event = KytosEvent(name=event_name, content=content)
        self.controller.buffers.msg_out.put(event)

    def _send_napp_event(self, switch, flow, command, **kwargs):
        """Send an Event to other apps informing about a FlowMod."""
        if command == "add":
            name = "kytos/flow_manager.flow.added"
        elif command in ("delete", "delete_strict"):
            name = "kytos/flow_manager.flow.removed"
        elif command == "error":
            name = "kytos/flow_manager.flow.error"
        else:
            raise InvalidCommandError
        content = {"datapath": switch, "flow": flow}
        content.update(kwargs)
        event_app = KytosEvent(name, content)
        self.controller.buffers.app.put(event_app)

    @listen_to(".*.of_core.*.ofpt_error")
    def handle_errors(self, event):
        """Receive OpenFlow error and send a event.

        The event is sent only if the error is related to a request made
        by flow_manager.
        """
        message = event.content["message"]

        connection = event.source
        switch = connection.switch

        xid = message.header.xid.value
        error_type = message.error_type
        error_code = message.code
        error_data = message.data.pack()

        # Get the packet responsible for the error
        error_packet = connection.protocol.unpack(error_data)

        if message.code == BadActionCode.OFPBAC_BAD_OUT_PORT:
            actions = []
            if hasattr(error_packet, "actions"):
                # Get actions from the flow mod (OF 1.0)
                actions = error_packet.actions
            else:
                # Get actions from the list of flow mod instructions (OF 1.3)
                for instruction in error_packet.instructions:
                    actions.extend(instruction.actions)

            for action in actions:
                iface = switch.get_interface_by_port_no(action.port)

                # Set interface to drop packets forwarded to it
                if iface:
                    iface.config = PortConfig.OFPPC_NO_FWD

        try:
            flow, error_command = self._flow_mods_sent[xid]
        except KeyError:
            pass
        else:
            self._send_napp_event(
                flow.switch,
                flow,
                "error",
                error_command=error_command,
                error_type=error_type,
                error_code=error_code,
            )
