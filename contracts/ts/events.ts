import type { SchemaVersion } from "./state";

export type EventType =
  | "GAME_STARTED"
  | "TURN_STARTED"
  | "DICE_ROLLED"
  | "PLAYER_MOVED"
  | "CASH_CHANGED"
  | "PROPERTY_PURCHASED"
  | "RENT_PAID"
  | "SENT_TO_JAIL"
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
  | RentPaidEvent
  | SentToJailEvent
  | TurnEndedEvent
  | GameEndedEvent
  | LlmDecisionRequestedEvent
  | LlmDecisionResponseEvent
  | LlmPublicMessageEvent
  | LlmPrivateThoughtEvent;
