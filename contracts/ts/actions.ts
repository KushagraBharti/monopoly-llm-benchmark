import type { SchemaVersion } from "./state";

export type ActionName =
  | "ROLL_DICE"
  | "BUY_PROPERTY"
  | "DECLINE_PROPERTY"
  | "START_AUCTION"
  | "PAY_BAIL"
  | "USE_JAIL_CARD"
  | "ROLL_FOR_DOUBLES"
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
  action: "BUY_PROPERTY";
  args: { space_index: number };
}

export interface DeclinePropertyAction extends BaseAction {
  action: "DECLINE_PROPERTY";
  args: { space_index: number };
}

export interface StartAuctionAction extends BaseAction {
  action: "START_AUCTION";
  args: { space_index: number };
}

export interface PayBailAction extends BaseAction {
  action: "PAY_BAIL";
  args: EmptyArgs;
}

export interface UseJailCardAction extends BaseAction {
  action: "USE_JAIL_CARD";
  args: EmptyArgs;
}

export interface RollForDoublesAction extends BaseAction {
  action: "ROLL_FOR_DOUBLES";
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
  | DeclinePropertyAction
  | StartAuctionAction
  | PayBailAction
  | UseJailCardAction
  | RollForDoublesAction
  | EndTurnAction
  | NoopAction;
