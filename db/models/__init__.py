"""DB models."""

# pylint: disable=unused-argument,invalid-name,unused-argument
# pylint: disable=no-self-argument,no-name-in-module


from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Union

from bson.decimal128 import Decimal128
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FlowEntryState(Enum):
    """Enum for stored Flow Entry states."""

    PENDING = "pending"  # initial state, it has been stored, but not confirmed yet
    INSTALLED = "installed"  # final state, when the installtion has been confirmed
    DELETED = "deleted"  # final state when the flow gets soft deleted


class DocumentBaseModel(BaseModel):
    """DocumentBaseModel."""

    id: str = Field(None, alias="_id")
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def model_dump(self, **kwargs) -> dict:
        """Model to dict."""
        values = super().model_dump(**kwargs)
        if "id" in values and values["id"]:
            values["_id"] = values["id"]
        if "exclude" in kwargs and "_id" in kwargs["exclude"]:
            values.pop("_id")
        return values


class FlowCheckDoc(DocumentBaseModel):
    """FlowCheckDoc."""

    state: str = Field(default="active")


class MatchSubDoc(BaseModel):
    """Match DB SubDocument Model."""

    in_port: Optional[int] = None
    dl_src: Optional[str] = None
    dl_dst: Optional[str] = None
    dl_type: Optional[int] = None
    dl_vlan: Optional[Union[int, str]] = None
    dl_vlan_pcp: Optional[int] = None
    nw_src: Optional[str] = None
    nw_dst: Optional[str] = None
    nw_proto: Optional[int] = None
    tp_src: Optional[int] = None
    tp_dst: Optional[int] = None
    in_phy_port: Optional[int] = None
    ip_dscp: Optional[int] = None
    ip_ecn: Optional[int] = None
    udp_src: Optional[int] = None
    udp_dst: Optional[int] = None
    sctp_src: Optional[int] = None
    sctp_dst: Optional[int] = None
    icmpv4_type: Optional[int] = None
    icmpv4_code: Optional[int] = None
    arp_op: Optional[int] = None
    arp_spa: Optional[str] = None
    arp_tpa: Optional[str] = None
    arp_sha: Optional[str] = None
    arp_tha: Optional[str] = None
    ipv6_src: Optional[str] = None
    ipv6_dst: Optional[str] = None
    ipv6_flabel: Optional[int] = None
    icmpv6_type: Optional[int] = None
    icmpv6_code: Optional[int] = None
    nd_tar: Optional[int] = None
    nd_sll: Optional[int] = None
    nd_tll: Optional[int] = None
    mpls_lab: Optional[int] = None
    mpls_tc: Optional[int] = None
    mpls_bos: Optional[int] = None
    pbb_isid: Optional[int] = None
    v6_hdr: Optional[int] = None
    metadata: Optional[int] = None
    tun_id: Optional[int] = None

    @field_validator("dl_vlan")
    @classmethod
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

    table_id: int = 0
    owner: Optional[str] = None
    table_group: str = "base"
    priority: int = 0x8000
    cookie: Decimal128 = Decimal128("0")
    idle_timeout: int = 0
    hard_timeout: int = 0
    match: Optional[MatchSubDoc] = None
    actions: Optional[List[dict]] = None
    instructions: Optional[List[dict]] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("cookie", mode="before")
    @classmethod
    def preset_cookie(cls, v, values, **kwargs) -> Decimal128:
        """Preset cookie."""
        if isinstance(v, (int, str)):
            return Decimal128(Decimal(v))
        return v

    @model_validator(mode="after")
    def validate_actions_intructions(self) -> dict:
        """Validate that actions and intructions are mutually exclusive"""
        if self.actions is not None and self.instructions is not None:
            raise ValueError(
                'Cannot have both "actions" and "instructions" at the same time'
            )
        return self


class FlowDoc(DocumentBaseModel):
    """Flow DB Document Model."""

    switch: str
    flow_id: str
    flow: FlowSubDoc
    state: str = FlowEntryState.PENDING.value
