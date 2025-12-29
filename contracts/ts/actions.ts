import type { SchemaVersion } from "./state";

export type ActionName =
  | "ROLL_DICE"
  | "buy_property"
  | "start_auction"
  | "pay_jail_fine"
  | "use_get_out_of_jail_card"
  | "roll_for_doubles"
  | "END_TURN"
  | "NOOP";

export type EmptyArgs = Record<string, never>;

export interface BaseAction {
  schema_version: SchemaVersion;
  decision_id: string;
  action: ActionName;
  args: Record<string, unknown>;
  public_message?: string;
  private_thought?: string;
}

export interface RollDiceAction extends BaseAction {
  action: "ROLL_DICE";
  args: EmptyArgs;
}

export interface BuyPropertyAction extends BaseAction {
  action: "buy_property";
  args: EmptyArgs;
}

export interface StartAuctionAction extends BaseAction {
  action: "start_auction";
  args: EmptyArgs;
}

export interface PayBailAction extends BaseAction {
  action: "pay_jail_fine";
  args: EmptyArgs;
}

export interface UseJailCardAction extends BaseAction {
  action: "use_get_out_of_jail_card";
  args: EmptyArgs;
}

export interface RollForDoublesAction extends BaseAction {
  action: "roll_for_doubles";
  args: EmptyArgs;
}

export interface EndTurnAction extends BaseAction {
  action: "END_TURN";
  args: EmptyArgs;
}

export interface NoopAction extends BaseAction {
  action: "NOOP";
  args: { reason: string };
}

export type Action =
  | RollDiceAction
  | BuyPropertyAction
  | StartAuctionAction
  | PayBailAction
  | UseJailCardAction
  | RollForDoublesAction
  | EndTurnAction
  | NoopAction;
