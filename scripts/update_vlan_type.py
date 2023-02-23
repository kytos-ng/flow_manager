from kytos.core.db import mongo_client

client = mongo_client()
collection = client["napps"]["flows"]
for flow in collection.find({"flow.match.dl_vlan": {"$exists": True}}):
    print(f"Updating flow {flow}")
    collection.update_one(
        {"_id": flow["_id"]},
        {"$set": {"flow.match.dl_vlan": str(flow["flow"]["match"]["dl_vlan"])}},
    )
