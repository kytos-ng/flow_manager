"""kytos/flow_manager NApp installs, lists and deletes switch flows."""

# pylint: disable=relative-beyond-top-level,too-many-function-args
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from flask import jsonify, request
from napps.kytos.flow_manager.match import match_flow
from napps.kytos.of_core.flow import FlowFactory
from napps.kytos.of_core.msg_prios import of_msg_prio
from napps.kytos.of_core.settings import STATS_INTERVAL
from napps.kytos.of_core.v0x04.flow import Flow as Flow04
from pyof.v0x04.asynchronous.error_msg import BadActionCode, ErrorType
from pyof.v0x04.common.header import Type
from pyof.v0x04.common.port import PortConfig
from werkzeug.exceptions import (
    BadRequest,
    FailedDependency,
    NotFound,
    UnsupportedMediaType,
)

from kytos.core import KytosEvent, KytosNApp, log, rest
from kytos.core.helpers import listen_to, now

from .barrier_request import new_barrier_request
from .controllers import FlowController
from .db.models import FlowEntryState
from .exceptions import InvalidCommandError, SwitchNotConnectedError
from .settings import (
    CONN_ERR_MAX_RETRIES,
    CONN_ERR_MIN_WAIT,
    CONN_ERR_MULTIPLIER,
    CONSISTENCY_COOKIE_IGNORED_RANGE,
    CONSISTENCY_MIN_VERDICT_INTERVAL,
    CONSISTENCY_TABLE_ID_IGNORED_RANGE,
    ENABLE_BARRIER_REQUEST,
    ENABLE_CONSISTENCY_CHECK,
    FLOWS_DICT_MAX_SIZE,
)
from .utils import (
    _valid_consistency_ignored,
    build_command_from_flow_mod,
    build_flow_mod_from_command,
    cast_fields,
    get_min_wait_diff,
    is_ignored,
)


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
        self._consistency_verdict = max(
            CONSISTENCY_MIN_VERDICT_INTERVAL, STATS_INTERVAL + STATS_INTERVAL // 2
        )

        self.flow_controller = self.get_flow_controller()
        self.flow_controller.bootstrap_indexes()

        self._flow_mods_sent_lock = Lock()

        self._pending_barrier_reply = defaultdict(OrderedDict)
        self._pending_barrier_lock = Lock()
        self._pending_barrier_max_size = FLOWS_DICT_MAX_SIZE

        self._flow_mods_sent_error = {}
        self._flow_mods_retry_count = {}
        self._flow_mods_retry_count_lock = Lock()
        self.resent_flows = set()

    @staticmethod
    def get_flow_controller() -> FlowController:
        """Get FlowController."""
        return FlowController()

    def execute(self):
        """Run once on NApp 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        pass

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    @listen_to("kytos/of_core.handshake.completed")
    def on_resend_stored_flows(self, event):
        """Resend stored Flows."""
        self.resend_stored_flows(event)

    def resend_stored_flows(self, event) -> None:
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
        for flow in self.flow_controller.get_flows(dpid):
            flows_dict = {"flows": [flow["flow"]]}
            try:
                self._install_flows("add", flows_dict, [switch], save=False)
                self.resent_flows.add(dpid)
            except SwitchNotConnectedError:
                log.error(f"Failed to resend flows to Switch {dpid}")
                # reraise to land on core dead letter
                raise
        log.info(f"Flows resent to Switch {dpid}")

    @listen_to("kytos/of_core.handshake.completed")
    def on_handshake_completed(self, event):
        """On switch connection handshake completed."""
        switch = event.content["switch"]
        if not switch:
            return
        self.reset_flow_check(switch.id)

    def reset_flow_check(self, dpid):
        """Reset flow check."""
        self.flow_controller.upsert_flow_check(dpid, state="inactive")

    @listen_to("kytos/of_core.flow_stats.received")
    def on_flow_stats_check_consistency(self, event):
        """Check the consistency of a switch upon receiving flow stats."""
        self.check_consistency(event.content["switch"])

    @listen_to("kytos/of_core.v0x04.messages.in.ofpt_flow_removed")
    def on_ofpt_flow_removed(self, event):
        """Listen to OFPT_FLOW_REMOVED and publish to subscribers."""
        self._on_ofpt_flow_removed(event)

    def _on_ofpt_flow_removed(self, event):
        """Publish kytos/flow_manager.flow.removed event to subscribers."""
        switch = event.source.switch
        flow = event.message
        self._send_napp_event(switch, flow, "delete")

    @listen_to("kytos/of_core.v0x04.messages.in.ofpt_barrier_reply")
    def on_ofpt_barrier_reply(self, event):
        """Listen to OFPT_BARRIER_REPLY.

        When a switch receives a Barrier message it must first complete all commands,
        sent before the Barrier message before executing any commands after it. Messages
        before a barrier must be fully processed before the barrier, including sending
        any resulting replies or errors. So, we can leverage this to confirm that a
        particular flow has been confirmed without having to scan for pending flows.

        """
        if not ENABLE_BARRIER_REQUEST:
            return
        self._on_ofpt_barrier_reply(event)

    # pylint: disable=pointless-string-statement
    def _on_ofpt_barrier_reply(self, event):
        """Process on_ofpt_barrier_reply event."""
        switch = event.source.switch
        message = event.message
        xid = int(message.header.xid)
        with self._pending_barrier_lock:
            flow_xids = self._pending_barrier_reply[switch.id].pop(xid, None)
            if not flow_xids:
                log.error(
                    f"Failed to pop barrier reply xid: {xid}, flow xids: {flow_xids}"
                )
                return

        flows = []
        with self._flow_mods_sent_lock:
            for flow_xid in flow_xids:
                flow, cmd = self._flow_mods_sent[flow_xid]
                if (
                    cmd != "add"
                    or flow_xid not in self._flow_mods_sent
                    or flow_xid in self._flow_mods_sent_error
                ):
                    continue
                flows.append(flow)
        """
        It should only publish installed flow if it the original FlowMod xid hasn't
        errored out. OFPT_ERROR messages could be received first if the barrier request
        hasn't been sent out or processed yet this can happen if the network latency
        is super low.
        """
        if flows:
            self._publish_installed_flow(switch, flows)

    def _publish_installed_flow(self, switch, flows):
        """Publish installed flow when it's confirmed."""
        for flow in flows:
            self._send_napp_event(switch, flow, "add")
        self.flow_controller.update_flows_state(
            [flow.id for flow in flows], FlowEntryState.INSTALLED.value
        )

    @listen_to("kytos/of_core.flow_stats.received")
    def on_flow_stats_publish_installed_flows(self, event):
        """Listen to flow stats to publish installed flows when they're confirmed."""
        self.publish_installed_flows(event.content["switch"])

    def publish_installed_flows(self, switch):
        """Publish installed flows when they're confirmed."""
        pending_flows = list(
            self.flow_controller.get_flows_by_state(
                switch.id, FlowEntryState.PENDING.value
            )
        )
        if not pending_flows:
            return

        installed_flows = self.switch_flows_by_id(switch, self.is_not_ignored_flow)

        flow_ids_to_update = []
        for flow in pending_flows:
            _id = flow["_id"]
            if _id not in installed_flows:
                continue

            installed_flow = installed_flows[_id]
            flow_ids_to_update.append(_id)
            self._send_napp_event(switch, installed_flow, "add")

        if flow_ids_to_update:
            self.flow_controller.update_flows_state(
                flow_ids_to_update, FlowEntryState.INSTALLED.value
            )

    def _retry_on_openflow_connection_error(
        self,
        event,
        max_retries=CONN_ERR_MAX_RETRIES,
        min_wait=CONN_ERR_MIN_WAIT,
        multiplier=CONN_ERR_MULTIPLIER,
        send_barrier=ENABLE_BARRIER_REQUEST,
    ):
        """Try to retry asynchronously on openflow connection error events.

        Args:
            event (KytoEvent): kytos/core.openflow.connection.error event.
            max_retries (int): Maximum number of asynchronous retries.
            min_wait (int): Minimum wait between iterations in seconds.
            multiplier (int): Multiplier for the accumulated wait on each iteration.
            send_barrier (bool): True to send barrier requests.

        Returns:
            bool: True if retried, False if max retries have been reached.
        """
        if max_retries <= 0:
            raise ValueError(f"max_retries: {max_retries} should be > 0")

        try:
            xid = int(event.message.header.xid)
            flow, command = self._flow_mods_sent[xid]
        except KeyError:
            raise ValueError(
                f"Aborting retries, xid: {xid} not found on flow mods sent"
            )
        switch = event.content["destination"].switch

        with self._flow_mods_retry_count_lock:
            if xid not in self._flow_mods_retry_count:
                self._flow_mods_retry_count[xid] = (0, now(), min_wait)
            (count, sent_at, wait_acc) = self._flow_mods_retry_count[xid]
            if count >= max_retries:
                log.warning(
                    f"Max retries: {max_retries} for xid: {xid} has been reached on "
                    f"switch {switch.id}, command: {command}, flow: {flow.as_dict()}"
                )
                self._send_openflow_connection_error(event)
                return False

            datetime_t2 = now()
            self._flow_mods_retry_count[xid] = (
                count + 1,
                datetime_t2,
                wait_acc * multiplier,
            )
        try:
            wait_diff = get_min_wait_diff(datetime_t2, sent_at, wait_acc)
            if wait_diff:
                time.sleep(wait_diff)
            log.info(
                f"Retry attempt: {count + 1} for xid: {xid} on switch: {switch.id}, "
                f"accumulated wait: {wait_acc}, command: {command}, "
                f"flow: {flow.as_dict()}"
            )
            flow_mod = build_flow_mod_from_command(flow, command)
            flow_mod.header.xid = xid
            self._send_flow_mod(flow.switch, flow_mod)
            if send_barrier:
                self._send_barrier_request(flow.switch, flow_mod)
            return True
        except SwitchNotConnectedError:
            log.info(f"Switch {switch.id} isn't connected, it'll retry.")
            return self._retry_on_openflow_connection_error(event, xid)

    def check_consistency(self, switch):
        """Check consistency of stored and installed flows given a switch."""
        if not ENABLE_CONSISTENCY_CHECK or not switch.is_enabled():
            return

        flow_check = self.flow_controller.get_flow_check(switch.id)
        verdict_dt = datetime.utcnow() - timedelta(seconds=self._consistency_verdict)

        # Skip, if the last relative run is within the verdict datetime
        if flow_check and flow_check["updated_at"] >= verdict_dt:
            return

        verdict_dt = verdict_dt if flow_check else None
        log.debug(f"check_consistency on switch {switch.id} has started")
        self.check_alien_flows(switch, verdict_dt)
        self.check_missing_flows(switch, verdict_dt)
        log.debug(f"check_consistency on switch {switch.id} is done")
        self.flow_controller.upsert_flow_check(switch.id)

    def is_not_ignored_flow(self, flow) -> bool:
        """Is not ignored flow."""
        if not is_ignored(flow.cookie, self.cookie_ignored_range) and not is_ignored(
            flow.table_id, self.tab_id_ignored_range
        ):
            return True
        return False

    @staticmethod
    def switch_flows_by_id(switch, filter_flow=lambda flow: True):
        """Build switch.flows indexed by id."""
        return {flow.id: flow for flow in switch.flows if filter_flow(flow)}

    def check_missing_flows(self, switch, verdict_dt: Optional[datetime] = None):
        """Check missing flows on a switch and install them."""
        verdict_dt = datetime.utcnow() if not verdict_dt else verdict_dt
        dpid = switch.dpid
        flows = self.switch_flows_by_id(switch, self.is_not_ignored_flow)
        for flow in self.flow_controller.get_flows_lte_updated_at(
            switch.id, verdict_dt
        ):
            if flow["flow_id"] not in flows:
                log.info(f"Consistency check: missing flow on switch {dpid}.")
                flow = {"flows": [flow["flow"]]}
                try:
                    self._install_flows("add", flow, [switch], save=False)
                    log.info(
                        f"Flow forwarded to switch {dpid} to be installed. Flow: {flow}"
                    )
                except SwitchNotConnectedError:
                    log.error(
                        f"Failed to forward flow to switch {dpid} to be installed. "
                        f"Flow: {flow}"
                    )

    def check_alien_flows(self, switch, verdict_dt: Optional[datetime] = None):
        """Check alien flows on a switch and delete them."""
        dpid = switch.dpid
        stored_by_flow_id = {}
        stored_by_match = {}
        deleted_by_flow_id = {}

        for flow in self.flow_controller.get_flows(switch.id):
            stored_by_flow_id[flow["flow_id"]] = flow
            stored_by_match[flow["id"]] = flow

        deleted_by_flow_id = {
            flow["flow_id"]: flow
            for flow in self.flow_controller.get_flows_by_state(
                switch.id, FlowEntryState.DELETED.value
            )
        }

        verdict_dt = datetime.utcnow() if not verdict_dt else verdict_dt
        flows = self.switch_flows_by_id(switch, self.is_not_ignored_flow)
        for flow_id, flow in flows.items():
            if flow_id not in stored_by_flow_id:
                if (
                    flow.match_id in stored_by_match
                    and stored_by_match[flow.match_id]["updated_at"] >= verdict_dt
                ):
                    continue

                if (
                    flow.id in deleted_by_flow_id
                    and deleted_by_flow_id[flow.id]["updated_at"] >= verdict_dt
                ):
                    continue

                log.info(f"Consistency check: alien flow on switch {dpid}")
                flow = {"flows": [flow.as_dict()]}
                command = "delete_strict"
                try:
                    self._install_flows(command, flow, [switch], save=False)
                    log.info(
                        f"Flow forwarded to switch {dpid} to be deleted. "
                        f"Flow: {flow}"
                    )
                    continue
                except SwitchNotConnectedError:
                    log.error(
                        f"Failed to forward flow to switch {dpid} to be deleted. "
                        f"Flow: {flow}"
                    )

    def delete_matched_flows(self, flow_dicts, switches: dict) -> None:
        """Try to delete many matched stored flows given flow_dicts for switches.

        This deletion tries to minimize DB round trips, it aggregates all
        included cookies grouped by dpids, and then at the runtime it performs
        a non strict match iterating over the flows if they haven't been deleted yet.
        If flows are matched, they will be bulk updated as deleted
        """
        deleted_flows = {}
        cookies = list(
            {
                int(value.get("cookie", 0)) & int(value.get("cookie_mask", 0))
                for value in [flow.get("flow", {}) for flow in flow_dicts]
            }
        )
        for dpid, stored_flows in self.flow_controller.get_flows_by_cookies(
            list(switches.keys()), cookies
        ).items():
            for flow_dict in flow_dicts:
                for stored_flow in stored_flows:
                    if stored_flow["id"] in deleted_flows:
                        continue
                    if match_flow(
                        flow_dict["flow"],
                        switches[dpid].connection.protocol.version
                        if dpid in switches
                        and switches[dpid].connection
                        and switches[dpid].connection.protocol
                        else 0x04,
                        stored_flow["flow"],
                    ):
                        stored_flow["state"] = FlowEntryState.DELETED.value
                        deleted_flows[stored_flow["id"]] = stored_flow
        if deleted_flows:
            self.flow_controller.upsert_flows(
                deleted_flows.keys(), deleted_flows.values()
            )

    # pylint: disable=attribute-defined-outside-init
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

    @rest("v2/stored_flows")
    def list_stored(self):
        """Retrieve stored flows (only installed flows by default),
        where `_id` is excluded in the response.

        It is possible dynamically parametrize the switches and state.
        `dpid` is as a list of dpids separated by comma.
        If `dpid` is not specified all documents are returned.
        """
        args = request.args
        dpids = args.getlist("dpid", type=str)
        state = args.get("state", type=str)
        if state is None:
            state = "installed"
        flows_collection = dict(self.flow_controller.find_flows(dpids, state))
        return jsonify(flows_collection)

    @listen_to("kytos.flow_manager.flows.(install|delete)")
    def on_flows_install_delete(self, event):
        """Install or delete flows in the switches through events.

        Install or delete Flow of switches identified by dpid.
        """
        self.handle_flows_install_delete(event)

    def handle_flows_install_delete(self, event):
        """Handle install/delete flows event."""
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

        force = bool(event.content.get("force", False))
        switch = self.controller.get_switch_by_dpid(dpid)
        log.info(
            f"Send FlowMod from KytosEvent dpid: {dpid}, command: {command}, "
            f"force: {force}, flows_dict: {flow_dict}"
        )
        try:
            self._install_flows(command, flow_dict, [switch], reraise_conn=not force)
        except InvalidCommandError as error:
            log.error(
                "Error installing or deleting Flow through" f" Kytos Event: {error}"
            )
        except SwitchNotConnectedError as error:
            self._send_napp_event(switch, error.flow, "error")

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

        force = bool(flows_dict.get("force", False))
        log.info(
            f"Send FlowMod from request dpid: {dpid}, command: {command}, "
            f"force: {force}, flows_dict: {flows_dict}"
        )
        try:
            if not dpid:
                self._install_flows(
                    command,
                    flows_dict,
                    self._get_all_switches_enabled(),
                    reraise_conn=not force,
                )
                return jsonify({"response": "FlowMod Messages Sent"}), 202

            switch = self.controller.get_switch_by_dpid(dpid)
            if not switch:
                return jsonify({"response": "dpid not found."}), 404

            if not switch.is_enabled() and command == "add":
                raise NotFound("switch is disabled.")

            self._install_flows(command, flows_dict, [switch], reraise_conn=not force)
            return jsonify({"response": "FlowMod Messages Sent"}), 202

        except SwitchNotConnectedError as error:
            raise FailedDependency(str(error))

    def _install_flows(
        self,
        command: str,
        flows_dict: dict,
        switches=[],
        save=True,
        reraise_conn=True,
        send_barrier=ENABLE_BARRIER_REQUEST,
    ):
        """Execute all procedures to bulk install flows in the switches.

        Args:
            command: Flow command to be installed
            flows_dict: Dictionary with flows to be installed in the switches.
            switches: A list of switches
            save: A boolean to save flows in the database
            reraise_conn: True to reraise switch connection errors
            send_barrier: True to send barrier_request
        """
        flow_mods, flows, flow_dicts = [], [], []
        for switch in switches:
            serializer = FlowFactory.get_class(switch, Flow04)
            flows_list = flows_dict.get("flows", [])
            for flow_dict in flows_list:
                flow = serializer.from_dict(flow_dict, switch)
                flow_mod = build_flow_mod_from_command(flow, command)
                flow_mods.append(flow_mod)
                flows.append(flow)
                flow_dicts.append(
                    {**{"flow": flow_dict}, **{"flow_id": flow.id, "switch": switch.id}}
                )
        if save and command == "add":
            self.flow_controller.upsert_flows(
                [flow.match_id for flow in flows], flow_dicts
            )
        if save and command == "delete":
            self.delete_matched_flows(
                flow_dicts, {switch.id: switch for switch in switches}
            )
        self._send_flow_mods(switches, flow_mods, flows, reraise_conn, send_barrier)

    def _send_flow_mods(
        self,
        switches,
        flow_mods,
        flows,
        reraise_conn=True,
        send_barrier=ENABLE_BARRIER_REQUEST,
    ):
        """Send FlowMod (and BarrierRequest) given a list of flow_dicts to switches."""
        for switch in switches:
            for i, (flow_mod, flow) in enumerate(zip(flow_mods, flows)):
                try:
                    self._send_flow_mod(switch, flow_mod)
                    if send_barrier and i == len(flow_mods) - 1:
                        self._send_barrier_request(switch, flow_mods)
                except SwitchNotConnectedError:
                    if reraise_conn:
                        raise
                with self._flow_mods_sent_lock:
                    self._add_flow_mod_sent(
                        flow_mod.header.xid,
                        flow,
                        build_command_from_flow_mod(flow_mod),
                    )
                self._send_napp_event(switch, flow, "pending")
        return flow_mods

    def _add_flow_mod_sent(self, xid, flow, command):
        """Add the flow mod to the list of flow mods sent."""
        if len(self._flow_mods_sent) >= self._flow_mods_sent_max_size:
            self._flow_mods_sent.popitem(last=False)
        self._flow_mods_sent[xid] = (flow, command)

    def _add_barrier_request(self, dpid, barrier_xid, flow_mods):
        """Add a barrier request."""
        if len(self._pending_barrier_reply[dpid]) >= self._pending_barrier_max_size:
            self._pending_barrier_reply[dpid].popitem(last=False)
        self._pending_barrier_reply[dpid][barrier_xid] = [
            flow_mod.header.xid for flow_mod in flow_mods
        ]

    def _send_barrier_request(self, switch, flow_mods):
        event_name = "kytos/flow_manager.messages.out.ofpt_barrier_request"
        if not switch.is_connected():
            raise SwitchNotConnectedError(
                f"switch {switch.id} isn't connected", flow_mods
            )

        barrier_request = new_barrier_request(switch.connection.protocol.version)
        barrier_xid = barrier_request.header.xid
        with self._pending_barrier_lock:
            self._add_barrier_request(switch.id, barrier_xid, flow_mods)

        content = {"destination": switch.connection, "message": barrier_request}
        event = KytosEvent(
            name=event_name,
            content=content,
            priority=of_msg_prio(Type.OFPT_BARRIER_REQUEST.value),
        )
        self.controller.buffers.msg_out.put(event)

    def _send_flow_mod(self, switch, flow_mod):
        if not switch.is_connected():
            raise SwitchNotConnectedError(
                f"switch {switch.id} isn't connected", flow_mod
            )

        event_name = "kytos/flow_manager.messages.out.ofpt_flow_mod"
        content = {"destination": switch.connection, "message": flow_mod}

        event = KytosEvent(
            name=event_name,
            content=content,
            priority=of_msg_prio(Type.OFPT_FLOW_MOD.value),
        )
        self.controller.buffers.msg_out.put(event)

    def _send_napp_event(self, switch, flow, command, **kwargs):
        """Send an Event to other apps informing about a FlowMod."""
        command_events = {
            "pending": "kytos/flow_manager.flow.pending",
            "add": "kytos/flow_manager.flow.added",
            "delete": "kytos/flow_manager.flow.removed",
            "delete_strict": "kytos/flow_manager.flow.removed",
            "error": "kytos/flow_manager.flow.error",
        }
        try:
            name = command_events[command]
        except KeyError as error:
            raise InvalidCommandError(str(error))
        content = {"datapath": switch, "flow": flow}
        content.update(kwargs)
        event_app = KytosEvent(name, content)
        self.controller.buffers.app.put(event_app)

    @listen_to("kytos/core.openflow.connection.error")
    def on_openflow_connection_error(self, event):
        """Listen to openflow connection error and publish the flow error."""
        try:
            self._retry_on_openflow_connection_error(event)
        except ValueError as exc:
            log.error(str(exc))

    def _send_openflow_connection_error(self, event):
        """Publish kytos/flow_manager.flow.error with an error_exception."""
        switch = event.content["destination"].switch
        flow = event.message
        try:
            _, error_command = self._flow_mods_sent[event.message.header.xid]
        except KeyError:
            error_command = "unknown"
        error_kwargs = {
            "error_command": error_command,
            "error_exception": event.content.get("exception"),
        }
        self._flow_mods_sent_error[int(event.message.header.xid)] = error_kwargs
        self._send_napp_event(
            switch,
            flow,
            "error",
            **error_kwargs,
        )

    @listen_to(".*.of_core.*.ofpt_error")
    def on_handle_errors(self, event):
        """Receive OpenFlow error and send a event.

        The event is sent only if the error is related to a request made
        by flow_manager.
        """
        self.handle_errors(event)

    def handle_errors(self, event):
        """handle OpenFlow error."""
        message = event.content["message"]
        error_type = message.error_type
        error_code = message.code
        if error_type == ErrorType.OFPET_HELLO_FAILED:
            return

        connection = event.source
        switch = connection.switch

        xid = message.header.xid.value
        error_data = message.data.pack()

        # Get the packet responsible for the error
        error_packet = connection.protocol.unpack(error_data)

        if message.code == BadActionCode.OFPBAC_BAD_OUT_PORT:
            actions = []
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
            error_kwargs = {
                "error_command": error_command,
                "error_type": error_type,
                "error_code": error_code,
            }
            self._flow_mods_sent_error[int(event.message.header.xid)] = error_kwargs
            log.warning(
                f"Deleting flow: {flow.as_dict()}, xid: {xid}, cookie: {flow.cookie}, "
                f"error: {error_kwargs}"
            )
            self.flow_controller.delete_flow_by_id(flow.id)
            self._send_napp_event(flow.switch, flow, "error", **error_kwargs)
