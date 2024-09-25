import os
from kytos.core.db import mongo_client
from bson.decimal128 import Decimal128
from decimal import Decimal


client = mongo_client()
collection = client[os.environ["MONGO_DBNAME"]]["flows"]

# Flows from mef_eline, table groups available: epl, evpl
query_match = {
    "flow.cookie": {
        "$gte": Decimal128(Decimal(12249790986447749120)),
        "$lte": Decimal128(Decimal(12321848580485677055)),
    },
    "flow.match.dl_vlan": {
        "$ne": None,
    }
}
update = {
    "$set": {
        "flow.owner": "mef_eline",
        "flow.table_group": "evpl"
    }
}
flows = collection.update_many(query_match, update)
print(f"{flows.modified_count} mef_eline flows were modified as EVPL.")

query_match = {
    "flow.cookie": {
        "$gte": Decimal128(Decimal(12249790986447749120)),
        "$lte": Decimal128(Decimal(12321848580485677055)),
    },
    "flow.match.dl_vlan": {
        "$eq": None,
    }
}
update = {
    "$set": {
        "flow.owner": "mef_eline",
        "flow.table_group": "epl"
    }
}
flows = collection.update_many(query_match, update)
print(f"{flows.modified_count} mef_eline flows were modified as EPL")

# Flows from of_lldp
query_match = {
    "flow.cookie": {
        "$gte": Decimal128(Decimal(12321848580485677056)),
        "$lte": Decimal128(Decimal(12393906174523604991)),
    }
}
update = {
    "$set": {
        "flow.owner": "of_lldp",
        "flow.table_group": "base"
    }
}
flows = collection.update_many(query_match, update)
print(f"{flows.modified_count} of_lldp flows were modified as base")

# Flows from coloring
query_match = {
    "flow.cookie": {
        "$gte": Decimal128(Decimal(12393906174523604992)),
        "$lte": Decimal128(Decimal(12465963768561532927)),
    }
}
update = {
    "$set": {
        "flow.owner": "coloring",
        "flow.table_group": "base"
    }
}
flows = collection.update_many(query_match, update)
print(f"{flows.modified_count} coloring flows were modified as base")

#Any other flow with cookie 0
query_match = {
    "flow.cookie": {"$eq": Decimal128(Decimal(0))}
}
update = {
    "$set": {"flow.table_group": "base"}
}
flows = collection.update_many(query_match, update)
print(f"{flows.modified_count} flows were modified as base")
