from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError


class EmptyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpaceIndexArgs(BaseModel):
    space_index: int = Field(ge=0, le=39)

    model_config = ConfigDict(extra="forbid")


class NoopArgs(BaseModel):
    reason: str

    model_config = ConfigDict(extra="forbid")


class ActionBase(BaseModel):
    schema_version: Literal["v1"]
    decision_id: str
    public_message: str | None = None
    private_thought: str | None = None

    model_config = ConfigDict(extra="forbid")


class RollDiceAction(ActionBase):
    action: Literal["ROLL_DICE"]
    args: EmptyArgs


class BuyPropertyAction(ActionBase):
    action: Literal["BUY_PROPERTY"]
    args: SpaceIndexArgs


class DeclinePropertyAction(ActionBase):
    action: Literal["DECLINE_PROPERTY"]
    args: SpaceIndexArgs


class StartAuctionAction(ActionBase):
    action: Literal["START_AUCTION"]
    args: SpaceIndexArgs


class PayBailAction(ActionBase):
    action: Literal["PAY_BAIL"]
    args: EmptyArgs


class UseJailCardAction(ActionBase):
    action: Literal["USE_JAIL_CARD"]
    args: EmptyArgs


class RollForDoublesAction(ActionBase):
    action: Literal["ROLL_FOR_DOUBLES"]
    args: EmptyArgs


class EndTurnAction(ActionBase):
    action: Literal["END_TURN"]
    args: EmptyArgs


class NoopAction(ActionBase):
    action: Literal["NOOP"]
    args: NoopArgs


ActionUnion = Union[
    RollDiceAction,
    BuyPropertyAction,
    DeclinePropertyAction,
    StartAuctionAction,
    PayBailAction,
    UseJailCardAction,
    RollForDoublesAction,
    EndTurnAction,
    NoopAction,
]


class ActionRoot(RootModel[ActionUnion]):
    pass


def validate_action_payload(action: dict[str, Any]) -> tuple[bool, list[str]]:
    try:
        ActionRoot.model_validate(action)
    except ValidationError as exc:
        return False, [f"{err['loc']}: {err['msg']}" for err in exc.errors()]
    return True, []
