import type { SchemaVersion, StateSnapshot } from "./state";

export type DecisionType =
  | "PRE_ROLL"
  | "POST_LAND"
  | "JAIL_CHOICE"
  | "BUY_DECISION"
  | "AUCTION_BID"
  | "END_TURN"
  | "TRADE_RESPONSE";

export interface UiHints {
  highlight_space_indices?: number[];
}

export interface EmptyArgsSchema {
  type: "object";
  additionalProperties: false;
}

export interface SpaceIndexArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["space_index"];
  properties: {
    space_index: {
      type: "integer";
      minimum: 0;
      maximum: 39;
    };
  };
}

export interface NoopArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["reason"];
  properties: {
    reason: {
      type: "string";
    };
  };
}

export interface BaseLegalAction {
  ui_hints?: UiHints;
}

export interface RollDiceLegalAction extends BaseLegalAction {
  action: "ROLL_DICE";
  args_schema: EmptyArgsSchema;
}

export interface BuyPropertyLegalAction extends BaseLegalAction {
  action: "BUY_PROPERTY";
  args_schema: SpaceIndexArgsSchema;
}

export interface DeclinePropertyLegalAction extends BaseLegalAction {
  action: "DECLINE_PROPERTY";
  args_schema: SpaceIndexArgsSchema;
}

export interface StartAuctionLegalAction extends BaseLegalAction {
  action: "START_AUCTION";
  args_schema: SpaceIndexArgsSchema;
}

export interface PayBailLegalAction extends BaseLegalAction {
  action: "PAY_BAIL";
  args_schema: EmptyArgsSchema;
}

export interface UseJailCardLegalAction extends BaseLegalAction {
  action: "USE_JAIL_CARD";
  args_schema: EmptyArgsSchema;
}

export interface RollForDoublesLegalAction extends BaseLegalAction {
  action: "ROLL_FOR_DOUBLES";
  args_schema: EmptyArgsSchema;
}

export interface EndTurnLegalAction extends BaseLegalAction {
  action: "END_TURN";
  args_schema: EmptyArgsSchema;
}

export interface NoopLegalAction extends BaseLegalAction {
  action: "NOOP";
  args_schema: NoopArgsSchema;
}

export type LegalAction =
  | RollDiceLegalAction
  | BuyPropertyLegalAction
  | DeclinePropertyLegalAction
  | StartAuctionLegalAction
  | PayBailLegalAction
  | UseJailCardLegalAction
  | RollForDoublesLegalAction
  | EndTurnLegalAction
  | NoopLegalAction;

export interface DecisionPoint {
  schema_version: SchemaVersion;
  run_id: string;
  decision_id: string;
  turn_index: number;
  player_id: string;
  decision_type: DecisionType;
  state: StateSnapshot;
  legal_actions: LegalAction[];
}
