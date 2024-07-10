#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import os
import pymongo
from uuid import uuid4
from datetime import datetime

from napps.kytos.flow_manager.controllers import FlowController
from napps.kytos.of_core.v0x04.flow import Flow as Flow04
from unittest.mock import MagicMock
from pymongo.operations import DeleteOne
from pymongo.operations import UpdateOne


flow_controller = FlowController()


def outdated_match_id_flows(flow_controller=flow_controller) -> dict[int, dict]:
    """Find outdated match_id flows indexed by their old_match_id."""
    flows = {}
    for dpid, flow_docs in flow_controller.find_flows().items():
        switch_mock = MagicMock()
        switch_mock.id = dpid
        for flow_doc in flow_docs:
            flow = Flow04.from_dict(flow_doc["flow"], switch_mock)
            if flow.match_id != flow_doc["id"]:
                old_id = flow_doc["id"]
                flow_doc["id"] = flow.match_id
                flows[old_id] = flow_doc
    return flows


def update_match_id_flows(flow_controller=flow_controller) -> dict:
    """Update the match_id of outdated match_id flows.

    - Outdated flows will first have its flow_id updated to avoid conflict
    - The new flows with updated match_id will be inserted
    - The outdated flows will be deleted

    """
    new_match_ids, new_flow_dicts, deleted_ops, pre_update = [], [], [], []
    for old_match_id, flow_doc in outdated_match_id_flows(flow_controller).items():
        new_match_ids.append(flow_doc["id"])
        flow_doc.pop("id")
        new_flow_dicts.append(flow_doc)

        deleted_ops.append(DeleteOne({"_id": old_match_id}))

        temp_flow_id = str(uuid4())
        pre_update.append(
            UpdateOne(
                {"flow_id": flow_doc["flow_id"]}, {"$set": {"flow_id": temp_flow_id}}
            )
        )

    pre_updated = (
        flow_controller.db.flows.bulk_write(pre_update).upserted_count
        if pre_update
        else 0
    )
    inserted = (
        len(flow_controller.upsert_flows(new_match_ids, new_flow_dicts))
        if new_match_ids
        else 0
    )
    deleted = (
        flow_controller.db.flows.bulk_write(deleted_ops).deleted_count
        if deleted_ops
        else 0
    )
    return {"inserted": inserted, "deleted": deleted, "pre_updated": pre_updated}


def write_file(flow_controller=flow_controller) -> str:
    """Write the findflows to a json file.
    This is meant as a helper step in case you wanted
    to diff the json files (before and after).
    """

    out_file = os.environ["OUT_FILE"]
    flows = flow_controller.find_flows()
    out_flows: dict[str, list[dict]] = {}
    for dpid in sorted(flows):
        flows[dpid].sort(key=lambda f: f["flow_id"])
        out_flows[dpid] = []
        for i, flow in enumerate(flows[dpid]):
            for k, v in flow.items():
                if isinstance(v, datetime):
                    flows[dpid][i][k] = str(v)
            out_flows[dpid].append(flow)
    with open(out_file, "w") as f:
        f.write(json.dumps(out_flows))
    return out_file


if __name__ == "__main__":
    cmds = {
        "count": lambda: {"to_delete": len(outdated_match_id_flows())},
        "update": update_match_id_flows,
        "write_file": write_file,
    }
    try:
        cmd = os.environ["CMD"]
    except KeyError:
        print("Please set the 'CMD' env var.")
        sys.exit(1)
    try:
        for command in cmd.split(","):
            print(cmds[command]())
    except KeyError as e:
        print(
            f"Unknown cmd: {str(e)}. 'CMD' env var has to be one of these {list(cmds.keys())}."
        )
        sys.exit(1)
    except pymongo.errors.PyMongoError as e:
        print(f"pymongo error: {str(e)}")
        sys.exit(1)
