#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest.mock import MagicMock
import json
import glob
import pickle
import os
import sys
from collections import defaultdict
from typing import Any
from napps.kytos.flow_manager.controllers import FlowController
from concurrent.futures import ThreadPoolExecutor, as_completed
from napps.kytos.of_core.v0x04.flow import Flow as Flow04

flow_controller = FlowController()


def get_storehouse_dir() -> str:
    return os.environ["STOREHOUSE_NAMESPACES_DIR"]


def _list_boxes_files(namespace: str, storehouse_dir=get_storehouse_dir()) -> dict:
    """List boxes files given the storehouse dir."""
    if storehouse_dir.endswith(os.path.sep):
        storehouse_dir = storehouse_dir[:-1]
    return {
        file_name.split(os.path.sep)[-2]: file_name
        for file_name in glob.glob(f"{storehouse_dir}/{namespace}**/*", recursive=True)
    }


def _load_from_file(file_name) -> Any:
    with open(file_name, "rb") as load_file:
        return pickle.load(load_file)


def load_boxes_data(namespace: str) -> dict:
    """Load boxes data."""
    return {k: _load_from_file(v).data for k, v in _list_boxes_files(namespace).items()}


def load_flows() -> dict:
    """Load flow_persistence namespace."""
    namespace = "kytos.flow.persistence"
    content = load_boxes_data(namespace)
    if namespace not in content:
        return {}

    content = content[namespace]
    if "flow_persistence" not in content:
        return {}
    content = content["flow_persistence"]

    switches = defaultdict(list)
    for dpid, values in content.items():
        for vals in values.values():
            for flow_dict in vals:
                switches[dpid].append(flow_dict)
    return switches


def insert_from_flow_persistence(
    flow_controller=flow_controller,
) -> list:
    """Insert from flow_persistence."""
    loaded_switches = load_flows()

    new_flows = {}
    for dpid, flows in loaded_switches.items():
        switch = MagicMock(id=dpid)
        for flow_dict in flows:
            flow_dict.pop("_id", None)
            flow = Flow04.from_dict(flow_dict["flow"], switch)
            flow_dict["switch"] = dpid
            flow_dict["flow_id"] = flow.id
            new_flows[flow.match_id] = flow_dict

    insert_flows = []
    with ThreadPoolExecutor(max_workers=len(new_flows)) as executor:
        futures = [
            executor.submit(flow_controller.upsert_flow, match_id, flow_dict)
            for match_id, flow_dict in new_flows.items()
        ]
        for future in as_completed(futures):
            response = future.result()
            insert_flows.append(response)

    return insert_flows


if __name__ == "__main__":
    cmds = {
        "insert_flows": insert_from_flow_persistence,
        "load_flows": lambda: json.dumps(load_flows()),
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
