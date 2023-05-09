"""DB models."""
# pylint: disable=unused-argument,invalid-name,unused-argument
# pylint: disable=no-self-argument,no-name-in-module


from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Union

from bson.decimal128 import Decimal128
from pydantic import BaseModel, Field, validator


class FlowEntryState(Enum):
    """Enum for stored Flow Entry states."""

    PENDING = "pending"  # initial state, it has been stored, but not confirmed yet
    INSTALLED = "installed"  # final state, when the installtion has been confirmed
    DELETED = "deleted"  # final state when the flow gets soft deleted


class DocumentBaseModel(BaseModel):
    """DocumentBaseModel."""

    id: str = Field(None, alias="_id")
    inserted_at: Optional[datetime]
    updated_at: Optional[datetime]

    def dict(self, **kwargs) -> dict:
        """Model to dict."""
        values = super().dict(**kwargs)
        if "id" in values and values["id"]:
            values["_id"] = values["id"]
        if "exclude" in kwargs and "_id" in kwargs["exclude"]:
            values.pop("_id")
        return values


class FlowCheckDoc(DocumentBaseModel):
    """FlowCheckDoc."""

    state = "active"


class MatchSubDoc(BaseModel):
    """Match DB SubDocument Model."""

    in_port: Optional[int]
    dl_src: Optional[str]
    dl_dst: Optional[str]
    dl_type: Optional[int]
    dl_vlan: Optional[Union[int, str]]
    dl_vlan_pcp: Optional[int]
    nw_src: Optional[str]
    nw_dst: Optional[str]
    nw_proto: Optional[int]
    tp_src: Optional[int]
    tp_dst: Optional[int]
    in_phy_port: Optional[int]
    ip_dscp: Optional[int]
    ip_ecn: Optional[int]
    udp_src: Optional[int]
    udp_dst: Optional[int]
    sctp_src: Optional[int]
    sctp_dst: Optional[int]
    icmpv4_type: Optional[int]
    icmpv4_code: Optional[int]
    arp_op: Optional[int]
    arp_spa: Optional[str]
    arp_tpa: Optional[str]
    arp_sha: Optional[str]
    arp_tha: Optional[str]
    ipv6_src: Optional[str]
    ipv6_dst: Optional[str]
    ipv6_flabel: Optional[int]
    icmpv6_type: Optional[int]
    icmpv6_code: Optional[int]
    nd_tar: Optional[int]
    nd_sll: Optional[int]
    nd_tll: Optional[int]
    mpls_lab: Optional[int]
    mpls_tc: Optional[int]
    mpls_bos: Optional[int]
    pbb_isid: Optional[int]
    v6_hdr: Optional[int]
    metadata: Optional[int]
    tun_id: Optional[int]

    @validator("dl_vlan")
    def vlan_with_mask(cls, v):
        """Validate vlan format"""
        try:
            return int(v)
        except ValueError:
            try:
                [int(part) for part in v.split("/")]
            except ValueError:
                raise ValueError(
                    "must be an integer or an integer with a mask in format vlan/mask"
                )
        return v


class FlowSubDoc(BaseModel):
    """Flow DB SubDocument Model."""

    table_id = 0
    owner: Optional[str]
    table_group = "base"
    priority = 0x8000
    cookie: Decimal128 = Decimal128("0")
    idle_timeout = 0
    hard_timeout = 0
    match: Optional[MatchSubDoc]
    actions: Optional[List[dict]]
    instructions: Optional[List[dict]]

    class Config:
        """Config."""

        arbitrary_types_allowed = True

    @validator("cookie", pre=True)
    def preset_cookie(cls, v, values, **kwargs) -> Decimal128:
        """Preset cookie."""
        if isinstance(v, (int, str)):
            return Decimal128(Decimal(v))
        return v


class FlowDoc(DocumentBaseModel):
    """Flow DB Document Model."""

    switch: str
    flow_id: str
    flow: FlowSubDoc
    state = FlowEntryState.PENDING.value
