export type SchemaVersion = "v1";

export type Phase =
  | "START_TURN"
  | "RESOLVING_MOVE"
  | "AWAITING_DECISION"
  | "END_TURN"
  | "GAME_OVER";

export interface Player {
  player_id: string;
  name: string;
  cash: number;
  position: number;
  in_jail: boolean;
  jail_turns: number;
  doubles_count: number;
  bankrupt: boolean;
  bankrupt_to: string | null;
  get_out_of_jail_cards: number;
}

export interface Bank {
  houses_remaining: number;
  hotels_remaining: number;
}

export type SpaceKind =
  | "GO"
  | "PROPERTY"
  | "RAILROAD"
  | "UTILITY"
  | "TAX"
  | "CHANCE"
  | "COMMUNITY_CHEST"
  | "JAIL"
  | "GO_TO_JAIL"
  | "FREE_PARKING";

export interface Space {
  index: number;
  kind: SpaceKind;
  name: string;
  group: string | null;
  price: number | null;
  owner_id: string | null;
  mortgaged: boolean;
  houses: number;
  hotel: boolean;
}

export interface DerivedState {
  net_worth_estimate_by_player?: Record<string, number>;
  monopolies_by_player?: Record<string, string[]>;
}

export interface StateSnapshot {
  schema_version: SchemaVersion;
  run_id: string;
  turn_index: number;
  phase: Phase;
  active_player_id: string;
  players: Player[];
  bank: Bank;
  board: Space[];
  derived?: DerivedState;
}
