from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SellerAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    ready: bool


class BuyerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=500)
    contains_sensitive_data: bool = False


class OrderStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1, max_length=80)
    seller_assets: list[SellerAsset] = Field(min_length=1, max_length=20)
    buyer_update: BuyerUpdate | None = None


class HandoffStage(StrEnum):
    SELLER_ASSETS = "seller_assets"
    BUYER_UPDATE = "buyer_update"
    ORDER_HANDOFF = "order_handoff"


def select_handoff_stage(request: OrderStreamRequest) -> HandoffStage:
    if any(not asset.ready for asset in request.seller_assets):
        return HandoffStage.SELLER_ASSETS
    if request.buyer_update is not None:
        return HandoffStage.BUYER_UPDATE
    return HandoffStage.ORDER_HANDOFF


def build_marketplace_prompt(request: OrderStreamRequest, stage: HandoffStage) -> str:
    asset_lines = "\n".join(
        f"- {asset.asset_id}: {asset.label}; ready={str(asset.ready).lower()}"
        for asset in request.seller_assets
    )
    buyer_line = (
        request.buyer_update.message
        if request.buyer_update and not request.buyer_update.contains_sensitive_data
        else "Withheld from model context."
    )
    return (
        "Draft the next concise marketplace update. Do not infer personal data.\n"
        f"Order: {request.order_id}\n"
        f"Workflow stage: {stage.value}\n"
        f"Seller assets:\n{asset_lines}\n"
        f"Buyer update: {buyer_line}"
    )

