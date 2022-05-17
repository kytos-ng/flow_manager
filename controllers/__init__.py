"""FlowController."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import pymongo
from bson.decimal128 import Decimal128
from pymongo.collection import ReturnDocument

from kytos.core import log
from kytos.core.db import Mongo

from ..db.models import FlowCheckDoc, FlowDoc


class FlowController:
    """FlowController."""

    def __init__(self, get_mongo=lambda: Mongo()) -> None:
        """FlowController."""
        self.mongo = get_mongo()
        self.db_client = self.mongo.client
        self.db = self.db_client[self.mongo.db_name]

    def bootstrap_indexes(self) -> None:
        """Bootstrap indexes."""
        index_tuples = [
            ("flows", [("flow_id", pymongo.ASCENDING)], {"unique": True}),
            ("flows", [("state", pymongo.ASCENDING)], {}),
            (
                "flows",
                [
                    ("switch", pymongo.ASCENDING),
                    ("flow.cookie", pymongo.ASCENDING),
                ],
                {},
            ),
        ]
        for collection, keys, kwargs in index_tuples:
            if self.mongo.bootstrap_index(collection, keys, **kwargs):
                log.info(f"Created DB index {keys}, collection: {collection})")

    def upsert_flow(self, match_id: str, flow_dict: dict) -> Optional[dict]:
        """Update or insert flow.

        Insertions and updates are indexed by match_id to minimize lookups.
        """
        utc_now = datetime.utcnow()
        model = FlowDoc(
            **{
                **flow_dict,
                **{"_id": match_id, "updated_at": utc_now},
            }
        )
        payload = model.dict(exclude={"inserted_at"}, exclude_none=True)
        updated = self.db.flows.find_one_and_update(
            {"_id": match_id},
            {
                "$set": payload,
                "$setOnInsert": {"inserted_at": utc_now},
            },
            return_document=ReturnDocument.AFTER,
            upsert=True,
        )
        return updated

    @staticmethod
    def _set_updated_at(update_expr: dict) -> None:
        """Set updated_at on $set expression."""
        if "$set" in update_expr:
            update_expr["$set"].update({"updated_at": datetime.utcnow()})
        else:
            update_expr.update({"$set": {"updated_at": datetime.utcnow()}})

    def update_flow_state(self, flow_id: str, state: str) -> Optional[dict]:
        """Update flow state."""
        return self._update_flow(flow_id, {"$set": {"state": state}})

    def _update_flow(self, flow_id: str, update_expr: dict) -> Optional[dict]:
        """Try to find one flow and update it given an update expression."""
        self._set_updated_at(update_expr)
        return self.db.flows.find_one_and_update(
            {"flow_id": flow_id},
            update_expr,
            return_document=ReturnDocument.AFTER,
        )

    def get_flows_by_cookie(self, dpid: str, cookie: int) -> List[dict]:
        """Get flows by cookie."""
        for flow in self.db.flows.find(
            {"switch": dpid, "flow.cookie": Decimal128(Decimal(cookie))}
        ):
            flow["flow"]["cookie"] = int(flow["flow"]["cookie"].to_decimal())
            yield flow

    def upsert_flow_check(self, dpid: str, state="active") -> Optional[dict]:
        """Update or insert flow check."""
        utc_now = datetime.utcnow()
        model = FlowCheckDoc(**{"_id": dpid, "state": state, "updated_at": utc_now})
        updated = self.db.flow_checks.find_one_and_update(
            {"_id": dpid},
            {
                "$set": model.dict(exclude={"inserted_at"}),
                "$setOnInsert": {"inserted_at": utc_now},
            },
            return_document=ReturnDocument.AFTER,
            upsert=True,
        )
        return updated

    def get_flow_check(self, dpid, state="active") -> Optional[dict]:
        """Get flow check."""
        return self.db.flow_checks.find_one({"_id": dpid, "state": state})
