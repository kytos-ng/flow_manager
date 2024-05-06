#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import pymongo

from napps.kytos.flow_manager.controllers import FlowController


flow_controller = FlowController()


def drop_index(index_name=None, flow_controller=flow_controller) -> dict:
    """drop_index."""
    index_name = index_name or os.environ.get(
        "INDEX_NAME", "switch_1_flow.cookie_1_state_1_inserted_at_1_updated_at_1"
    )
    return flow_controller.db.flows.drop_index(index_name)


if __name__ == "__main__":
    cmds = {
        "drop_index": drop_index,
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
