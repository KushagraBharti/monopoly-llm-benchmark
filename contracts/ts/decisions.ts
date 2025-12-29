import type { SchemaVersion, StateSnapshot } from "./state";

export type DecisionType =
  | "PRE_ROLL"
  | "POST_LAND"
  | "JAIL_DECISION"
  | "BUY_OR_AUCTION_DECISION"
  | "POST_TURN_ACTION_DECISION"
  | "LIQUIDATION_DECISION"
  | "AUCTION_BID_DECISION"
  | "TRADE_PROPOSE_DECISION"
  | "TRADE_RESPONSE_DECISION"
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

export interface SpaceKeyArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["space_key"];
  properties: {
    space_key: {
      type: "string";
    };
  };
}

export interface BidAmountArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["bid_amount"];
  properties: {
    bid_amount: {
      type: "integer";
      minimum: 0;
    };
  };
}

export interface TradeBundleSchema {
  type: "object";
  additionalProperties: false;
  required: ["cash", "properties", "get_out_of_jail_cards"];
  properties: {
    cash: {
      type: "integer";
      minimum: 0;
    };
    properties: {
      type: "array";
      items: {
        type: "string";
      };
    };
    get_out_of_jail_cards: {
      type: "integer";
      minimum: 0;
    };
  };
}

export interface ProposeTradeArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["to_player_id", "offer", "request"];
  properties: {
    to_player_id: {
      type: "string";
    };
    offer: TradeBundleSchema;
    request: TradeBundleSchema;
  };
}

export interface CounterTradeArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["offer", "request"];
  properties: {
    offer: TradeBundleSchema;
    request: TradeBundleSchema;
  };
}

export interface BuildPlanItemSchema {
  type: "object";
  additionalProperties: false;
  required: ["space_key", "kind", "count"];
  properties: {
    space_key: {
      type: "string";
    };
    kind: {
      type: "string";
      enum: ["HOUSE", "HOTEL"];
    };
    count: {
      type: "integer";
      minimum: 1;
    };
  };
}

export interface BuildPlanArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["build_plan"];
  properties: {
    build_plan: {
      type: "array";
      minItems: 1;
      items: BuildPlanItemSchema;
    };
  };
}

export interface SellPlanArgsSchema {
  type: "object";
  additionalProperties: false;
  required: ["sell_plan"];
  properties: {
    sell_plan: {
      type: "array";
      minItems: 1;
      items: BuildPlanItemSchema;
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
  action: "buy_property";
  args_schema: EmptyArgsSchema;
}

export interface StartAuctionLegalAction extends BaseLegalAction {
  action: "start_auction";
  args_schema: EmptyArgsSchema;
}

export interface BidAuctionLegalAction extends BaseLegalAction {
  action: "bid_auction";
  args_schema: BidAmountArgsSchema;
}

export interface DropOutLegalAction extends BaseLegalAction {
  action: "drop_out";
  args_schema: EmptyArgsSchema;
}

export interface ProposeTradeLegalAction extends BaseLegalAction {
  action: "propose_trade";
  args_schema: ProposeTradeArgsSchema;
}

export interface AcceptTradeLegalAction extends BaseLegalAction {
  action: "accept_trade";
  args_schema: EmptyArgsSchema;
}

export interface RejectTradeLegalAction extends BaseLegalAction {
  action: "reject_trade";
  args_schema: EmptyArgsSchema;
}

export interface CounterTradeLegalAction extends BaseLegalAction {
  action: "counter_trade";
  args_schema: CounterTradeArgsSchema;
}

export interface PayJailFineLegalAction extends BaseLegalAction {
  action: "pay_jail_fine";
  args_schema: EmptyArgsSchema;
}

export interface UseJailCardLegalAction extends BaseLegalAction {
  action: "use_get_out_of_jail_card";
  args_schema: EmptyArgsSchema;
}

export interface RollForDoublesLegalAction extends BaseLegalAction {
  action: "roll_for_doubles";
  args_schema: EmptyArgsSchema;
}

export interface EndTurnLegalAction extends BaseLegalAction {
  action: "end_turn";
  args_schema: EmptyArgsSchema;
}

export interface MortgagePropertyLegalAction extends BaseLegalAction {
  action: "mortgage_property";
  args_schema: SpaceKeyArgsSchema;
}

export interface UnmortgagePropertyLegalAction extends BaseLegalAction {
  action: "unmortgage_property";
  args_schema: SpaceKeyArgsSchema;
}

export interface BuildHousesOrHotelLegalAction extends BaseLegalAction {
  action: "build_houses_or_hotel";
  args_schema: BuildPlanArgsSchema;
}

export interface SellHousesOrHotelLegalAction extends BaseLegalAction {
  action: "sell_houses_or_hotel";
  args_schema: SellPlanArgsSchema;
}

export interface DeclareBankruptcyLegalAction extends BaseLegalAction {
  action: "declare_bankruptcy";
  args_schema: EmptyArgsSchema;
}

export interface NoopLegalAction extends BaseLegalAction {
  action: "NOOP";
  args_schema: NoopArgsSchema;
}

export type LegalAction =
  | RollDiceLegalAction
  | BuyPropertyLegalAction
  | StartAuctionLegalAction
  | BidAuctionLegalAction
  | DropOutLegalAction
  | ProposeTradeLegalAction
  | AcceptTradeLegalAction
  | RejectTradeLegalAction
  | CounterTradeLegalAction
  | PayJailFineLegalAction
  | UseJailCardLegalAction
  | RollForDoublesLegalAction
  | EndTurnLegalAction
  | MortgagePropertyLegalAction
  | UnmortgagePropertyLegalAction
  | BuildHousesOrHotelLegalAction
  | SellHousesOrHotelLegalAction
  | DeclareBankruptcyLegalAction
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
  post_turn?: {
    options: {
      can_trade_with: string[];
      mortgageable_space_indices: number[];
      unmortgageable_space_indices: number[];
      buildable_space_indices: number[];
      sellable_building_space_indices: number[];
    };
  };
  liquidation?: {
    owed_amount: number;
    owed_to_player_id?: string | null;
    reason: string;
    shortfall: number;
    options: {
      mortgageable_space_indices: number[];
      sellable_building_space_indices: number[];
    };
  };
}
