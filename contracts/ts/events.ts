import type { SchemaVersion } from "./state";

export type EventType =
  | "GAME_STARTED"
  | "TURN_STARTED"
  | "DICE_ROLLED"
  | "PLAYER_MOVED"
  | "CASH_CHANGED"
  | "PROPERTY_PURCHASED"
  | "PROPERTY_TRANSFERRED"
  | "AUCTION_STARTED"
  | "AUCTION_BID_PLACED"
  | "AUCTION_PLAYER_DROPPED"
  | "AUCTION_ENDED"
  | "TRADE_PROPOSED"
  | "TRADE_COUNTERED"
  | "TRADE_ACCEPTED"
  | "TRADE_REJECTED"
  | "TRADE_EXPIRED"
  | "RENT_PAID"
  | "SENT_TO_JAIL"
  | "CARD_DRAWN"
  | "HOUSE_BUILT"
  | "HOTEL_BUILT"
  | "HOUSE_SOLD"
  | "HOTEL_SOLD"
  | "PROPERTY_MORTGAGED"
  | "PROPERTY_UNMORTGAGED"
  | "TURN_ENDED"
  | "GAME_ENDED"
  | "LLM_DECISION_REQUESTED"
  | "LLM_DECISION_RESPONSE"
  | "LLM_PUBLIC_MESSAGE"
  | "LLM_PRIVATE_THOUGHT";

export type ActorKind = "ENGINE" | "PLAYER" | "ARENA" | "SYSTEM";

export interface Actor {
  kind: ActorKind;
  player_id: string | null;
}

export interface BaseEvent {
  schema_version: SchemaVersion;
  run_id: string;
  event_id: string;
  seq: number;
  turn_index: number;
  ts_ms: number;
  actor: Actor;
  type: EventType;
  payload: Record<string, unknown>;
}

export interface GameStartedEvent extends BaseEvent {
  type: "GAME_STARTED";
  payload: Record<string, never>;
}

export interface TurnStartedEvent extends BaseEvent {
  type: "TURN_STARTED";
  payload: Record<string, never>;
}

export interface DiceRolledEvent extends BaseEvent {
  type: "DICE_ROLLED";
  payload: {
    d1: number;
    d2: number;
    is_double: boolean;
    reason?: string;
  };
}

export interface PlayerMovedEvent extends BaseEvent {
  type: "PLAYER_MOVED";
  payload: {
    from: number;
    to: number;
    passed_go: boolean;
  };
}

export interface CashChangedEvent extends BaseEvent {
  type: "CASH_CHANGED";
  payload: {
    player_id: string;
    delta: number;
    reason: string;
  };
}

export interface PropertyPurchasedEvent extends BaseEvent {
  type: "PROPERTY_PURCHASED";
  payload: {
    player_id: string;
    space_index: number;
    price: number;
  };
}

export interface PropertyTransferredEvent extends BaseEvent {
  type: "PROPERTY_TRANSFERRED";
  payload: {
    from_player_id: string | null;
    to_player_id: string | null;
    space_index: number;
    mortgaged: boolean;
  };
}

export interface AuctionStartedEvent extends BaseEvent {
  type: "AUCTION_STARTED";
  payload: {
    property_space: string;
    initiator_player_id: string;
  };
}

export interface AuctionBidPlacedEvent extends BaseEvent {
  type: "AUCTION_BID_PLACED";
  payload: {
    property_space: string;
    bidder_player_id: string;
    bid_amount: number;
  };
}

export interface AuctionPlayerDroppedEvent extends BaseEvent {
  type: "AUCTION_PLAYER_DROPPED";
  payload: {
    property_space: string;
    player_id: string;
  };
}

export interface AuctionEndedEvent extends BaseEvent {
  type: "AUCTION_ENDED";
  payload: {
    property_space: string;
    winner_player_id: string | null;
    winning_bid: number | null;
    reason: "SOLD" | "NO_BIDS";
  };
}

export type TradeBundle = {
  cash: number;
  properties: string[];
  get_out_of_jail_cards: number;
};

export interface TradePayload extends Record<string, unknown> {
  initiator_player_id: string;
  counterparty_player_id: string;
  exchange_index: number;
  max_exchanges: number;
  offer: TradeBundle;
  request: TradeBundle;
  reason?: string;
}

export interface TradeProposedEvent extends BaseEvent {
  type: "TRADE_PROPOSED";
  payload: TradePayload;
}

export interface TradeCounteredEvent extends BaseEvent {
  type: "TRADE_COUNTERED";
  payload: TradePayload;
}

export interface TradeAcceptedEvent extends BaseEvent {
  type: "TRADE_ACCEPTED";
  payload: TradePayload;
}

export interface TradeRejectedEvent extends BaseEvent {
  type: "TRADE_REJECTED";
  payload: TradePayload;
}

export interface TradeExpiredEvent extends BaseEvent {
  type: "TRADE_EXPIRED";
  payload: TradePayload;
}

export interface RentPaidEvent extends BaseEvent {
  type: "RENT_PAID";
  payload: {
    from_player_id: string;
    to_player_id: string;
    amount: number;
    space_index: number;
  };
}

export interface SentToJailEvent extends BaseEvent {
  type: "SENT_TO_JAIL";
  payload: {
    player_id: string;
    reason: string;
  };
}

export interface CardDrawnEvent extends BaseEvent {
  type: "CARD_DRAWN";
  payload: {
    deck_type: "CHANCE" | "COMMUNITY_CHEST";
    card_id: string;
  };
}

export interface HouseBuiltEvent extends BaseEvent {
  type: "HOUSE_BUILT";
  payload: {
    player_id: string;
    space_index: number;
    count: number;
  };
}

export interface HotelBuiltEvent extends BaseEvent {
  type: "HOTEL_BUILT";
  payload: {
    player_id: string;
    space_index: number;
    count: number;
  };
}

export interface HouseSoldEvent extends BaseEvent {
  type: "HOUSE_SOLD";
  payload: {
    player_id: string;
    space_index: number;
    count: number;
  };
}

export interface HotelSoldEvent extends BaseEvent {
  type: "HOTEL_SOLD";
  payload: {
    player_id: string;
    space_index: number;
    count: number;
  };
}

export interface PropertyMortgagedEvent extends BaseEvent {
  type: "PROPERTY_MORTGAGED";
  payload: {
    player_id: string;
    space_index: number;
    amount: number;
  };
}

export interface PropertyUnmortgagedEvent extends BaseEvent {
  type: "PROPERTY_UNMORTGAGED";
  payload: {
    player_id: string;
    space_index: number;
    amount: number;
  };
}

export interface TurnEndedEvent extends BaseEvent {
  type: "TURN_ENDED";
  payload: Record<string, never>;
}

export interface GameEndedEvent extends BaseEvent {
  type: "GAME_ENDED";
  payload: {
    winner_player_id: string;
    reason: string;
  };
}

export interface LlmDecisionRequestedEvent extends BaseEvent {
  type: "LLM_DECISION_REQUESTED";
  payload: {
    decision_id: string;
    player_id: string;
    decision_type: string;
  };
}

export interface LlmDecisionResponseEvent extends BaseEvent {
  type: "LLM_DECISION_RESPONSE";
  payload: {
    decision_id: string;
    player_id: string;
    action_name: string;
    valid: boolean;
    error: string | null;
  };
}

export interface LlmPublicMessageEvent extends BaseEvent {
  type: "LLM_PUBLIC_MESSAGE";
  payload: {
    player_id: string;
    message: string;
    decision_id?: string;
  };
}

export interface LlmPrivateThoughtEvent extends BaseEvent {
  type: "LLM_PRIVATE_THOUGHT";
  payload: {
    player_id: string;
    thought: string;
    decision_id?: string;
  };
}

export type Event =
  | GameStartedEvent
  | TurnStartedEvent
  | DiceRolledEvent
  | PlayerMovedEvent
  | CashChangedEvent
  | PropertyPurchasedEvent
  | PropertyTransferredEvent
  | AuctionStartedEvent
  | AuctionBidPlacedEvent
  | AuctionPlayerDroppedEvent
  | AuctionEndedEvent
  | TradeProposedEvent
  | TradeCounteredEvent
  | TradeAcceptedEvent
  | TradeRejectedEvent
  | TradeExpiredEvent
  | RentPaidEvent
  | SentToJailEvent
  | CardDrawnEvent
  | HouseBuiltEvent
  | HotelBuiltEvent
  | HouseSoldEvent
  | HotelSoldEvent
  | PropertyMortgagedEvent
  | PropertyUnmortgagedEvent
  | TurnEndedEvent
  | GameEndedEvent
  | LlmDecisionRequestedEvent
  | LlmDecisionResponseEvent
  | LlmPublicMessageEvent
  | LlmPrivateThoughtEvent;
