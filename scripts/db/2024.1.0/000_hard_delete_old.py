#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import pymongo
from datetime import datetime

from napps.kytos.flow_manager.controllers import FlowController


flow_controller = FlowController()


def _deleted_lte_filter_expr() -> dict:
    """Get del filter expr."""
    dt = datetime.strptime(os.environ["UTC_DATETIME"], "%Y-%m-%d %H:%M:%S")
    filter_exp = {"state": "deleted", "updated_at": {"$lte": dt}}
    return filter_exp


def list_deleted_flows_updated_at_lte(flow_controller=flow_controller) -> None:
    """list deleted flows <= updated_at."""
    for flow in flow_controller.db.flows.find(_deleted_lte_filter_expr()):
        print(flow)


def count_deleted_flows_updated_at_lte(flow_controller=flow_controller) -> int:
    """Count deleted flows <= updated_at."""
    acc = 0
    for flow in flow_controller.db.flows.find(_deleted_lte_filter_expr()):
        acc += 1
    return acc


def delete_deleted_flows_updated_at_lte(flow_controller=flow_controller) -> dict:
    """list deleted flows <= updated_at."""
    return {
        "deleted": flow_controller.db.flows.delete_many(
            _deleted_lte_filter_expr()
        ).deleted_count
    }


if __name__ == "__main__":
    cmds = {
        "count": lambda: {"counted": count_deleted_flows_updated_at_lte()},
        "list": list_deleted_flows_updated_at_lte,
        "delete": delete_deleted_flows_updated_at_lte,
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
