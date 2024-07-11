#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
import os
import pymongo
from datetime import datetime

from napps.kytos.flow_manager.controllers import FlowController


flow_controller = FlowController()


def list_deleted_flows_updated_at_lte(flow_controller=flow_controller) -> list:
    """list deleted flows <= updated_at."""
    dt = datetime.strptime(os.environ["UTC_DATETIME"], "%Y-%m-%d %H:%M:%S")
    filter_exp = {"state": "deleted", "updated_at": {"$lte": dt}}
    return list(flow_controller.db.flows.find(filter_exp))


def delete_deleted_flows_updated_at_lte(flow_controller=flow_controller) -> dict:
    """list deleted flows <= updated_at."""
    dt = datetime.strptime(os.environ["UTC_DATETIME"], "%Y-%m-%d %H:%M:%S")
    filter_exp = {"state": "deleted", "updated_at": {"$lte": dt}}
    return {"deleted": flow_controller.db.flows.delete_many(filter_exp).deleted_count}


def write_file(flow_controller=flow_controller) -> str:
    """Write the findflows to a json file."""

    out_file = os.environ["OUT_FILE"]
    flows = list_deleted_flows_updated_at_lte(flow_controller)
    out_flows = []
    for i, flow in enumerate(flows):
        for k, v in flow.items():
            if isinstance(v, datetime):
                flows[i][k] = str(v)
        if "cookie" in flow["flow"]:
            flows[i]["flow"]["cookie"] = int(flows[i]["flow"]["cookie"].to_decimal())
        out_flows.append(flow)
    with open(out_file, "w") as f:
        f.write(json.dumps(out_flows))
    return out_file


if __name__ == "__main__":
    cmds = {
        "count": lambda: {"to_delete": len(list_deleted_flows_updated_at_lte())},
        "list": list_deleted_flows_updated_at_lte,
        "delete": delete_deleted_flows_updated_at_lte,
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
