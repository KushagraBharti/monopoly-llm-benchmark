import type { SchemaVersion } from "./state";

export type ActionName =
  | "ROLL_DICE"
  | "buy_property"
  | "start_auction"
  | "pay_jail_fine"
  | "use_get_out_of_jail_card"
  | "roll_for_doubles"
  | "end_turn"
  | "mortgage_property"
  | "unmortgage_property"
  | "build_houses_or_hotel"
  | "sell_houses_or_hotel"
  | "declare_bankruptcy"
  | "NOOP";

export type EmptyArgs = Record<string, never>;
export type SpaceKeyArgs = { space_key: string };

export type BuildingKind = "HOUSE" | "HOTEL";

export interface BuildPlanItem {
  space_key: string;
  kind: BuildingKind;
  count: number;
}

export interface BuildPlanArgs {
  build_plan: BuildPlanItem[];
}

export interface SellPlanArgs {
  sell_plan: BuildPlanItem[];
}

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
  action: "end_turn";
  args: EmptyArgs;
}

export interface MortgagePropertyAction extends BaseAction {
  action: "mortgage_property";
  args: SpaceKeyArgs;
}

export interface UnmortgagePropertyAction extends BaseAction {
  action: "unmortgage_property";
  args: SpaceKeyArgs;
}

export interface BuildHousesOrHotelAction extends BaseAction {
  action: "build_houses_or_hotel";
  args: BuildPlanArgs;
}

export interface SellHousesOrHotelAction extends BaseAction {
  action: "sell_houses_or_hotel";
  args: SellPlanArgs;
}

export interface DeclareBankruptcyAction extends BaseAction {
  action: "declare_bankruptcy";
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
  | MortgagePropertyAction
  | UnmortgagePropertyAction
  | BuildHousesOrHotelAction
  | SellHousesOrHotelAction
  | DeclareBankruptcyAction
  | NoopAction;
