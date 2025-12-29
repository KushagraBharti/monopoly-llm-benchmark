from __future__ import annotations

import math
from typing import Any

from .board import (
    GROUP_INDEXES,
    HOUSE_COST_BY_GROUP,
    OWNABLE_KINDS,
    PROPERTY_RENT_TABLES,
    RAILROAD_RENTS,
    SPACE_INDEX_BY_KEY,
    TAX_AMOUNTS,
    UTILITY_RENT_MULTIPLIER,
    build_board,
    normalize_space_key,
)
from .cards import CHANCE_CARDS, COMMUNITY_CHEST_CARDS
from .models import BankState, GameState, PlayerState, SpaceState
from .rng import DeterministicRng

DecisionPoint = dict[str, Any]
Event = dict[str, Any]
StepResult = tuple[GameState, list[Event], DecisionPoint | None, dict[str, Any] | None]

JAIL_FINE = 50
HOUSE_LIMIT = 4
HOTEL_HOUSE_EQUIV = 5
CHANCE_REPAIR_HOUSE_COST = 25
CHANCE_REPAIR_HOTEL_COST = 100
COMMUNITY_REPAIR_HOUSE_COST = 40
COMMUNITY_REPAIR_HOTEL_COST = 115
UTILITY_CARD_MULTIPLIER = 10


class Engine:
    def __init__(
        self,
        *,
        seed: int,
        players: list[dict[str, Any]],
        run_id: str,
        max_turns: int = 30,
        start_ts_ms: int = 0,
        ts_step_ms: int = 250,
    ) -> None:
        self.run_id = run_id
        self._rng = DeterministicRng(seed)
        self._max_turns = max_turns
        self._start_ts_ms = start_ts_ms
        self._ts_step_ms = ts_step_ms
        self._seq = 0
        self._started = False
        self._stop_reason: str | None = None
        self._decision_seq = 0
        self._pending_decision: DecisionPoint | None = None
        self._pending_turn: dict[str, Any] | None = None
        self._pending_payment: dict[str, Any] | None = None
        self.state = create_initial_state(run_id, seed, players)
        self._jail_index = next(
            (space.index for space in self.state.board if space.kind == "JAIL"),
            10,
        )
        self._chance_deck = self._rng.shuffle(CHANCE_CARDS)
        self._community_chest_deck = self._rng.shuffle(COMMUNITY_CHEST_CARDS)
        self._jail_card_sources: dict[str, list[str]] = {
            player.player_id: [] for player in self.state.players
        }
        self._space_index_by_name = {space.name: space.index for space in self.state.board}

    def request_stop(self, reason: str = "STOPPED") -> None:
        self._stop_reason = reason

    def is_game_over(self) -> bool:
        return self.state.phase == "GAME_OVER"

    def get_snapshot(self) -> dict[str, Any]:
        return self.state.to_snapshot()

    def advance_until_decision(self, max_steps: int = 1) -> StepResult:
        events: list[Event] = []
        snapshot: dict[str, Any] | None = None

        if max_steps <= 0:
            return self.state, events, self._pending_decision, snapshot

        if not self._started:
            events.append(self._build_event("GAME_STARTED", self._actor_engine(), {}, turn_index=0))
            self._started = True

        if self._pending_decision is not None:
            snapshot = self.get_snapshot()
            return self.state, events, self._pending_decision, snapshot

        if self.is_game_over():
            return self.state, events, None, snapshot

        steps = 0
        while steps < max_steps and not self.is_game_over():
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
                break
            turn_events, decision = self._run_turn()
            events.extend(turn_events)
            snapshot = self.get_snapshot()
            if decision is not None:
                return self.state, events, decision, snapshot
            steps += 1
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
                break

        return self.state, events, None, snapshot

    def apply_action(
        self,
        action: dict[str, Any],
        *,
        decision_meta: dict[str, Any] | None = None,
    ) -> StepResult:
        events: list[Event] = []
        snapshot: dict[str, Any] | None = None

        if self._pending_decision is None or self._pending_turn is None:
            raise ValueError("No pending decision to apply.")

        decision = self._pending_decision
        error = self._validate_action(action, decision)
        if error:
            raise ValueError(error)

        pending_turn = self._pending_turn
        player_id = decision["player_id"]
        meta_valid = True
        meta_error = None
        if decision_meta is not None:
            meta_valid = bool(decision_meta.get("valid", True))
            meta_error = decision_meta.get("error")
        events.append(
            self._build_event(
                "LLM_DECISION_RESPONSE",
                self._actor_player(player_id),
                {
                    "decision_id": decision["decision_id"],
                    "player_id": player_id,
                    "action_name": action["action"],
                    "valid": meta_valid,
                    "error": meta_error,
                },
                turn_index=self.state.turn_index,
            )
        )

        if "public_message" in action:
            events.append(
                self._build_event(
                    "LLM_PUBLIC_MESSAGE",
                    self._actor_player(player_id),
                    {
                        "player_id": player_id,
                        "message": action["public_message"],
                        "decision_id": decision["decision_id"],
                    },
                    turn_index=self.state.turn_index,
                )
            )
        if "private_thought" in action:
            events.append(
                self._build_event(
                    "LLM_PRIVATE_THOUGHT",
                    self._actor_player(player_id),
                    {
                        "player_id": player_id,
                        "thought": action["private_thought"],
                        "decision_id": decision["decision_id"],
                    },
                    turn_index=self.state.turn_index,
                )
            )

        action_name = action["action"]
        player = self._find_player(player_id)
        if player is None:
            raise ValueError(f"Unknown player for decision: {player_id}")

        decision_type = decision.get("decision_type")
        self._pending_decision = None
        self._pending_turn = None

        if decision_type == "BUY_OR_AUCTION_DECISION":
            space_index = int(pending_turn.get("space_index", 0))
            if action_name == "buy_property":
                space = self.state.board[space_index]
                self._apply_property_purchase(player, space, events)
            elif action_name == "start_auction":
                pass
            else:
                raise ValueError(f"Unsupported action: {action_name}")

            rolled_double = bool(pending_turn.get("rolled_double", False))
            decision = self._maybe_start_post_turn_decision(
                events,
                player,
                rolled_double=rolled_double,
            )
            snapshot = self.get_snapshot()
            if decision is not None:
                return self.state, events, decision, snapshot
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
            return self.state, events, None, snapshot

        if decision_type == "JAIL_DECISION":
            if action_name == "pay_jail_fine":
                self._apply_cash_delta(
                    player,
                    -JAIL_FINE,
                    "JAIL_FINE",
                    events,
                    turn_index=self.state.turn_index,
                )
                player.in_jail = False
                player.jail_turns = 0
                decision = self._roll_and_move(player, events, turn_index=self.state.turn_index)
                snapshot = self.get_snapshot()
                if decision is not None:
                    return self.state, events, decision, snapshot
                if self._should_end_game():
                    self._finish_game(events)
                    snapshot = self.get_snapshot()
                return self.state, events, None, snapshot

            if action_name == "use_get_out_of_jail_card":
                if player.get_out_of_jail_cards <= 0:
                    raise ValueError("No get out of jail cards available.")
                player.get_out_of_jail_cards -= 1
                self._return_jail_card(player)
                player.in_jail = False
                player.jail_turns = 0
                decision = self._roll_and_move(player, events, turn_index=self.state.turn_index)
                snapshot = self.get_snapshot()
                if decision is not None:
                    return self.state, events, decision, snapshot
                if self._should_end_game():
                    self._finish_game(events)
                    snapshot = self.get_snapshot()
                return self.state, events, None, snapshot

            if action_name == "roll_for_doubles":
                d1, d2 = self._rng.roll_dice()
                is_double = d1 == d2
                self.state.phase = "RESOLVING_MOVE"
                events.append(
                    self._build_event(
                        "DICE_ROLLED",
                        self._actor_player(player.player_id),
                        {"d1": d1, "d2": d2, "is_double": is_double},
                        turn_index=self.state.turn_index,
                    )
                )
                if not is_double:
                    player.jail_turns += 1
                    if player.jail_turns >= 3:
                        if player.cash < JAIL_FINE:
                            self._handle_bankruptcy(
                                player, None, events, turn_index=self.state.turn_index
                            )
                            player.in_jail = False
                            player.jail_turns = 0
                            self._end_turn(events, player, allow_extra_turn=False)
                            snapshot = self.get_snapshot()
                            if self._should_end_game():
                                self._finish_game(events)
                                snapshot = self.get_snapshot()
                            return self.state, events, None, snapshot
                        decision = self._build_jail_decision(player)
                        self.state.phase = "AWAITING_DECISION"
                        self._pending_decision = decision
                        self._pending_turn = {
                            "player_id": player.player_id,
                            "decision_type": "JAIL_DECISION",
                        }
                        events.append(
                            self._build_event(
                                "LLM_DECISION_REQUESTED",
                                self._actor_engine(),
                                {
                                    "decision_id": decision["decision_id"],
                                    "player_id": player.player_id,
                                    "decision_type": decision["decision_type"],
                                },
                                turn_index=self.state.turn_index,
                            )
                        )
                        snapshot = self.get_snapshot()
                        return self.state, events, decision, snapshot
                    self._end_turn(events, player, allow_extra_turn=False)
                    snapshot = self.get_snapshot()
                    if self._should_end_game():
                        self._finish_game(events)
                        snapshot = self.get_snapshot()
                    return self.state, events, None, snapshot

                player.in_jail = False
                player.jail_turns = 0
                player.doubles_count = 0
                decision, decision_space_index = self._move_player(
                    player,
                    d1 + d2,
                    events,
                    turn_index=self.state.turn_index,
                    rolled_double=False,
                )
                snapshot = self.get_snapshot()
                if decision is not None:
                    self.state.phase = "AWAITING_DECISION"
                    self._pending_decision = decision
                    self._pending_turn = {
                        "rolled_double": False,
                        "space_index": (
                            decision_space_index
                            if decision_space_index is not None
                            else player.position
                        ),
                        "player_id": player.player_id,
                    }
                    events.append(
                        self._build_event(
                            "LLM_DECISION_REQUESTED",
                            self._actor_engine(),
                            {
                                "decision_id": decision["decision_id"],
                                "player_id": player.player_id,
                                "decision_type": decision["decision_type"],
                            },
                            turn_index=self.state.turn_index,
                        )
                    )
                    return self.state, events, decision, snapshot
                decision = self._maybe_start_post_turn_decision(
                    events,
                    player,
                    rolled_double=False,
                )
                snapshot = self.get_snapshot()
                if decision is not None:
                    return self.state, events, decision, snapshot
                if self._should_end_game():
                    self._finish_game(events)
                    snapshot = self.get_snapshot()
                return self.state, events, None, snapshot

            raise ValueError(f"Unsupported action: {action_name}")

        if decision_type == "POST_TURN_ACTION_DECISION":
            rolled_double = bool(pending_turn.get("rolled_double", False))
            if action_name == "end_turn":
                pass
            elif action_name == "mortgage_property":
                self._apply_mortgage(player, action, events)
            elif action_name == "unmortgage_property":
                self._apply_unmortgage(player, action, events)
            elif action_name == "build_houses_or_hotel":
                self._apply_build_plan(player, action, events)
            elif action_name == "sell_houses_or_hotel":
                self._apply_sell_plan(player, action, events)
            else:
                raise ValueError(f"Unsupported action: {action_name}")

            self._end_turn(
                events,
                player,
                allow_extra_turn=rolled_double and not player.bankrupt and not player.in_jail,
            )
            snapshot = self.get_snapshot()
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
            return self.state, events, None, snapshot

        if decision_type == "LIQUIDATION_DECISION":
            pending_payment = self._pending_payment
            if pending_payment is None:
                raise ValueError("Missing pending payment context for liquidation.")
            if action_name == "declare_bankruptcy":
                payment = pending_payment.get("payment", {})
                creditor_id = pending_payment.get("owed_to_player_id") or payment.get("to_player_id")
                creditor = self._find_player(creditor_id) if creditor_id else None
                self._handle_bankruptcy(player, creditor, events, turn_index=self.state.turn_index)
                self._pending_payment = None
                self._end_turn(events, player, allow_extra_turn=False)
                snapshot = self.get_snapshot()
                if self._should_end_game():
                    self._finish_game(events)
                    snapshot = self.get_snapshot()
                return self.state, events, None, snapshot
            if action_name == "mortgage_property":
                self._apply_mortgage(player, action, events)
            elif action_name == "sell_houses_or_hotel":
                self._apply_sell_plan(player, action, events)
            else:
                raise ValueError(f"Unsupported action: {action_name}")

            decision = self._resolve_pending_payment(player, events, turn_index=self.state.turn_index)
            snapshot = self.get_snapshot()
            if decision is not None:
                return self.state, events, decision, snapshot
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
            return self.state, events, None, snapshot

        raise ValueError(f"Unsupported decision type: {decision_type}")

    def build_summary(self) -> dict[str, Any]:
        winner_id = self._determine_winner()
        return {
            "run_id": self.run_id,
            "winner_player_id": winner_id,
            "turn_count": self.state.turn_index,
            "reason": self._stop_reason or "TURN_LIMIT",
        }

    def _run_turn(self) -> tuple[list[Event], DecisionPoint | None]:
        events: list[Event] = []
        current_player = self._current_player()
        if current_player.bankrupt:
            self.state.active_player_id = self._next_active_player_id(current_player.player_id)
            return events, None

        turn_index = self.state.turn_index
        current_id = current_player.player_id

        self.state.phase = "START_TURN"
        self.state.active_player_id = current_id
        events.append(self._build_event("TURN_STARTED", self._actor_engine(), {}, turn_index=turn_index))

        if current_player.in_jail:
            if current_player.jail_turns >= 3 and current_player.cash < JAIL_FINE:
                self._handle_bankruptcy(current_player, None, events, turn_index=turn_index)
                current_player.in_jail = False
                current_player.jail_turns = 0
                self._end_turn(events, current_player, allow_extra_turn=False)
                return events, None
            decision = self._build_jail_decision(current_player)
            self.state.phase = "AWAITING_DECISION"
            self._pending_decision = decision
            self._pending_turn = {"player_id": current_id, "decision_type": "JAIL_DECISION"}
            events.append(
                self._build_event(
                    "LLM_DECISION_REQUESTED",
                    self._actor_engine(),
                    {
                        "decision_id": decision["decision_id"],
                        "player_id": current_id,
                        "decision_type": decision["decision_type"],
                    },
                    turn_index=turn_index,
                )
            )
            return events, decision

        d1, d2 = self._rng.roll_dice()
        is_double = d1 == d2
        if is_double:
            current_player.doubles_count += 1
        else:
            current_player.doubles_count = 0

        self.state.phase = "RESOLVING_MOVE"
        events.append(
            self._build_event(
                "DICE_ROLLED",
                self._actor_player(current_id),
                {"d1": d1, "d2": d2, "is_double": is_double},
                turn_index=turn_index,
            )
        )

        if is_double and current_player.doubles_count >= 3:
            self._send_player_to_jail(
                current_player,
                events,
                reason="THREE_DOUBLES",
                turn_index=turn_index,
            )
            self._end_turn(events, current_player, allow_extra_turn=False)
            return events, None

        decision, decision_space_index = self._move_player(
            current_player,
            d1 + d2,
            events,
            turn_index=turn_index,
            rolled_double=is_double,
        )
        if decision is not None:
            self.state.phase = "AWAITING_DECISION"
            self._pending_decision = decision
            self._pending_turn = {
                "rolled_double": is_double,
                "space_index": (
                    decision_space_index if decision_space_index is not None else current_player.position
                ),
                "player_id": current_id,
            }
            events.append(
                self._build_event(
                    "LLM_DECISION_REQUESTED",
                    self._actor_engine(),
                    {
                        "decision_id": decision["decision_id"],
                        "player_id": current_id,
                        "decision_type": decision["decision_type"],
                    },
                    turn_index=turn_index,
                )
            )
            return events, decision

        post_decision = self._maybe_start_post_turn_decision(
            events,
            current_player,
            rolled_double=is_double,
        )
        return events, post_decision

    def _move_player(
        self,
        player: PlayerState,
        steps: int,
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> tuple[DecisionPoint | None, int | None]:
        from_pos = player.position
        board_size = len(self.state.board)
        to_pos = (from_pos + steps) % board_size
        passed_go = to_pos < from_pos
        player.position = to_pos
        events.append(
            self._build_event(
                "PLAYER_MOVED",
                self._actor_player(player.player_id),
                {"from": from_pos, "to": to_pos, "passed_go": passed_go},
                turn_index=turn_index,
            )
        )
        if passed_go:
            self._apply_cash_delta(player, 200, "PASS_GO", events, turn_index=turn_index)
        space = self.state.board[to_pos]
        decision, decision_space_index = self._resolve_landing(
            player,
            space,
            steps,
            events,
            turn_index=turn_index,
            rolled_double=rolled_double,
        )
        return decision, decision_space_index

    def _send_player_to_jail(
        self,
        player: PlayerState,
        events: list[Event],
        *,
        reason: str,
        turn_index: int,
    ) -> None:
        from_pos = player.position
        player.position = self._jail_index
        player.in_jail = True
        player.jail_turns = 0
        player.doubles_count = 0
        if from_pos != self._jail_index:
            events.append(
                self._build_event(
                    "PLAYER_MOVED",
                    self._actor_player(player.player_id),
                    {"from": from_pos, "to": self._jail_index, "passed_go": False},
                    turn_index=turn_index,
                )
            )
        events.append(
            self._build_event(
                "SENT_TO_JAIL",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "reason": reason},
                turn_index=turn_index,
            )
        )

    def _roll_and_move(
        self,
        player: PlayerState,
        events: list[Event],
        *,
        turn_index: int,
    ) -> DecisionPoint | None:
        d1, d2 = self._rng.roll_dice()
        return self._move_after_roll(player, d1, d2, events, turn_index=turn_index)

    def _move_after_roll(
        self,
        player: PlayerState,
        d1: int,
        d2: int,
        events: list[Event],
        *,
        turn_index: int,
    ) -> DecisionPoint | None:
        is_double = d1 == d2
        if is_double:
            player.doubles_count += 1
        else:
            player.doubles_count = 0
        self.state.phase = "RESOLVING_MOVE"
        events.append(
            self._build_event(
                "DICE_ROLLED",
                self._actor_player(player.player_id),
                {"d1": d1, "d2": d2, "is_double": is_double},
                turn_index=turn_index,
            )
        )
        if is_double and player.doubles_count >= 3:
            self._send_player_to_jail(
                player,
                events,
                reason="THREE_DOUBLES",
                turn_index=turn_index,
            )
            self._end_turn(events, player, allow_extra_turn=False)
            return None
        decision, decision_space_index = self._move_player(
            player,
            d1 + d2,
            events,
            turn_index=turn_index,
            rolled_double=is_double,
        )
        if decision is not None:
            self.state.phase = "AWAITING_DECISION"
            self._pending_decision = decision
            self._pending_turn = {
                "rolled_double": is_double,
                "space_index": (
                    decision_space_index if decision_space_index is not None else player.position
                ),
                "player_id": player.player_id,
            }
            events.append(
                self._build_event(
                    "LLM_DECISION_REQUESTED",
                    self._actor_engine(),
                    {
                        "decision_id": decision["decision_id"],
                        "player_id": player.player_id,
                        "decision_type": decision["decision_type"],
                    },
                    turn_index=turn_index,
                )
            )
            return decision
        return self._maybe_start_post_turn_decision(events, player, rolled_double=is_double)

    def _resolve_landing(
        self,
        player: PlayerState,
        space: SpaceState,
        dice_total: int,
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> tuple[DecisionPoint | None, int | None]:
        if space.kind == "CHANCE":
            return self._draw_card(
                "CHANCE",
                player,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
        if space.kind == "COMMUNITY_CHEST":
            return self._draw_card(
                "COMMUNITY_CHEST",
                player,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
        if space.kind in OWNABLE_KINDS:
            if space.owner_id is None:
                self.state.phase = "AWAITING_DECISION"
                return self._build_buy_or_auction_decision(player, space), space.index
            if space.owner_id == player.player_id:
                return None, None
            owner = self._find_player(space.owner_id)
            if owner is None or owner.bankrupt or space.mortgaged:
                return None, None
            rent = self._calculate_rent(space, owner, dice_total)
            if rent > 0:
                decision = self._pay_rent(
                    player,
                    owner,
                    rent,
                    space.index,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
                if decision is not None:
                    return decision, space.index
            return None, None
        if space.kind == "TAX":
            amount = TAX_AMOUNTS.get(space.index, 0)
            if amount > 0:
                reason = "TAX_INCOME" if space.index == 4 else "TAX_LUXURY"
                decision = self._pay_tax(
                    player,
                    amount,
                    reason,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
                if decision is not None:
                    return decision, space.index
            return None, None
        if space.kind == "GO_TO_JAIL":
            self._send_player_to_jail(
                player,
                events,
                reason="GO_TO_JAIL",
                turn_index=turn_index,
            )
        return None, None

    def _draw_card(
        self,
        deck_type: str,
        player: PlayerState,
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> tuple[DecisionPoint | None, int | None]:
        deck = self._chance_deck if deck_type == "CHANCE" else self._community_chest_deck
        if not deck:
            return None, None
        card_id = deck.pop(0)
        events.append(
            self._build_event(
                "CARD_DRAWN",
                self._actor_player(player.player_id),
                {"deck_type": deck_type, "card_id": card_id},
                turn_index=turn_index,
            )
        )
        if card_id == "GET_OUT_OF_JAIL_FREE":
            player.get_out_of_jail_cards += 1
            self._jail_card_sources.setdefault(player.player_id, []).append(deck_type)
            return None, None
        decision, decision_space_index = self._apply_card_effect(
            deck_type,
            card_id,
            player,
            events,
            turn_index=turn_index,
            rolled_double=rolled_double,
        )
        deck.append(card_id)
        return decision, decision_space_index

    def _apply_card_effect(
        self,
        deck_type: str,
        card_id: str,
        player: PlayerState,
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> tuple[DecisionPoint | None, int | None]:
        if card_id == "ADVANCE_TO_GO":
            return self._move_player_to(
                player,
                0,
                events,
                turn_index=turn_index,
                collect_go=True,
                rolled_double=rolled_double,
            )
        if card_id == "GO_TO_ILLINOIS_AVE":
            target = self._space_index_by_name.get("Illinois Avenue", 24)
            return self._move_player_to(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=True,
                rolled_double=rolled_double,
            )
        if card_id == "GO_TO_ST_CHARLES_PLACE":
            target = self._space_index_by_name.get("St. Charles Place", 11)
            return self._move_player_to(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=True,
                rolled_double=rolled_double,
            )
        if card_id in {"GO_TO_NEAREST_UTILITY"}:
            target = self._find_next_index(player.position, "UTILITY")
            space = self.state.board[target]
            self._move_player_no_resolve(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=True,
            )
            if space.owner_id is None or space.owner_id == player.player_id or space.mortgaged:
                return self._resolve_landing(
                    player,
                    space,
                    0,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
            owner = self._find_player(space.owner_id)
            if owner is None or owner.bankrupt:
                return None, None
            d1, d2 = self._rng.roll_dice()
            events.append(
                self._build_event(
                    "DICE_ROLLED",
                    self._actor_player(player.player_id),
                    {"d1": d1, "d2": d2, "is_double": d1 == d2, "reason": "CARD_UTILITY_RENT"},
                    turn_index=turn_index,
                )
            )
            amount = (d1 + d2) * UTILITY_CARD_MULTIPLIER
            payment = self._build_payment_entry(
                amount,
                owner.player_id,
                "RENT",
                kind="RENT",
                space_index=space.index,
            )
            decision = self._request_payment(
                player,
                payment,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, space.index
        if card_id in {"GO_TO_NEAREST_RAILROAD_A", "GO_TO_NEAREST_RAILROAD_B"}:
            target = self._find_next_index(player.position, "RAILROAD")
            space = self.state.board[target]
            self._move_player_no_resolve(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=True,
            )
            if space.owner_id is None or space.owner_id == player.player_id or space.mortgaged:
                return self._resolve_landing(
                    player,
                    space,
                    0,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
            owner = self._find_player(space.owner_id)
            if owner is None or owner.bankrupt:
                return None, None
            owned = self._count_owned(owner.player_id, "RAILROAD")
            if owned <= 0:
                return None, None
            rent = RAILROAD_RENTS[min(owned, 4) - 1] * 2
            payment = self._build_payment_entry(
                rent,
                owner.player_id,
                "RENT",
                kind="RENT",
                space_index=space.index,
            )
            decision = self._request_payment(
                player,
                payment,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, space.index
        if card_id == "BANK_PAYS_YOU_DIVIDEND_50":
            self._apply_cash_delta(player, 50, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "GO_BACK_3_SPACES":
            target = (player.position - 3) % len(self.state.board)
            return self._move_player_to(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=False,
                rolled_double=rolled_double,
            )
        if card_id == "GO_TO_JAIL":
            self._send_player_to_jail(
                player,
                events,
                reason=f"{deck_type}_CARD",
                turn_index=turn_index,
            )
            return None, None
        if card_id == "GENERAL_REPAIRS":
            total = self._repairs_cost(
                player.player_id,
                CHANCE_REPAIR_HOUSE_COST,
                CHANCE_REPAIR_HOTEL_COST,
            )
            if total > 0:
                payment = self._build_payment_entry(total, None, card_id, kind="CARD")
                decision = self._request_payment(
                    player,
                    payment,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
                if decision is None:
                    return None, None
                return decision, player.position
            return None, None
        if card_id == "PAY_POOR_TAX_15":
            payment = self._build_payment_entry(15, None, card_id, kind="CARD")
            decision = self._request_payment(
                player,
                payment,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, player.position
        if card_id == "TAKE_TRIP_TO_READING_RR":
            target = self._space_index_by_name.get("Reading Railroad", 5)
            return self._move_player_to(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=True,
                rolled_double=rolled_double,
            )
        if card_id == "ADVANCE_TO_BOARDWALK":
            target = self._space_index_by_name.get("Boardwalk", 39)
            return self._move_player_to(
                player,
                target,
                events,
                turn_index=turn_index,
                collect_go=True,
                rolled_double=rolled_double,
            )
        if card_id == "ELECTED_CHAIRMAN_PAY_EACH_PLAYER_50":
            payments = [
                self._build_payment_entry(50, other.player_id, card_id, kind="CARD")
                for other in self.state.players
                if other.player_id != player.player_id and not other.bankrupt
            ]
            decision = self._process_payment_queue(
                player,
                payments,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, player.position
        if card_id == "BUILDING_LOAN_MATURES_RECEIVE_150":
            self._apply_cash_delta(player, 150, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "BANK_ERROR_COLLECT_200":
            self._apply_cash_delta(player, 200, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "DOCTOR_FEE_PAY_50":
            payment = self._build_payment_entry(50, None, card_id, kind="CARD")
            decision = self._request_payment(
                player,
                payment,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, player.position
        if card_id == "SALE_OF_STOCK_COLLECT_50":
            self._apply_cash_delta(player, 50, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "HOLIDAY_FUND_RECEIVE_100":
            self._apply_cash_delta(player, 100, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "INCOME_TAX_REFUND_COLLECT_20":
            self._apply_cash_delta(player, 20, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "BIRTHDAY_COLLECT_10_FROM_EACH_PLAYER":
            for other in self.state.players:
                if other.player_id == player.player_id or other.bankrupt:
                    continue
                if other.cash >= 10:
                    self._apply_cash_delta(other, -10, card_id, events, turn_index=turn_index)
                    self._apply_cash_delta(player, 10, card_id, events, turn_index=turn_index)
                else:
                    self._handle_bankruptcy(other, player, events, turn_index=turn_index)
            return None, None
        if card_id == "LIFE_INSURANCE_COLLECT_100":
            self._apply_cash_delta(player, 100, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "HOSPITAL_FEES_PAY_100":
            payment = self._build_payment_entry(100, None, card_id, kind="CARD")
            decision = self._request_payment(
                player,
                payment,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, player.position
        if card_id == "SCHOOL_FEES_PAY_50":
            payment = self._build_payment_entry(50, None, card_id, kind="CARD")
            decision = self._request_payment(
                player,
                payment,
                events,
                turn_index=turn_index,
                rolled_double=rolled_double,
            )
            if decision is None:
                return None, None
            return decision, player.position
        if card_id == "CONSULTANCY_FEE_COLLECT_25":
            self._apply_cash_delta(player, 25, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "STREET_REPAIRS":
            total = self._repairs_cost(
                player.player_id,
                COMMUNITY_REPAIR_HOUSE_COST,
                COMMUNITY_REPAIR_HOTEL_COST,
            )
            if total > 0:
                payment = self._build_payment_entry(total, None, card_id, kind="CARD")
                decision = self._request_payment(
                    player,
                    payment,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
                if decision is None:
                    return None, None
                return decision, player.position
            return None, None
        if card_id == "BEAUTY_CONTEST_COLLECT_10":
            self._apply_cash_delta(player, 10, card_id, events, turn_index=turn_index)
            return None, None
        if card_id == "INHERIT_100":
            self._apply_cash_delta(player, 100, card_id, events, turn_index=turn_index)
            return None, None
        return None, None

    def _move_player_to(
        self,
        player: PlayerState,
        target_index: int,
        events: list[Event],
        *,
        turn_index: int,
        collect_go: bool,
        rolled_double: bool,
    ) -> tuple[DecisionPoint | None, int | None]:
        target = self._move_player_no_resolve(
            player,
            target_index,
            events,
            turn_index=turn_index,
            collect_go=collect_go,
        )
        space = self.state.board[target]
        return self._resolve_landing(
            player,
            space,
            0,
            events,
            turn_index=turn_index,
            rolled_double=rolled_double,
        )

    def _move_player_no_resolve(
        self,
        player: PlayerState,
        target_index: int,
        events: list[Event],
        *,
        turn_index: int,
        collect_go: bool,
    ) -> int:
        from_pos = player.position
        board_size = len(self.state.board)
        target = target_index % board_size
        passed_go = collect_go and target < from_pos
        player.position = target
        events.append(
            self._build_event(
                "PLAYER_MOVED",
                self._actor_player(player.player_id),
                {"from": from_pos, "to": target, "passed_go": passed_go},
                turn_index=turn_index,
            )
        )
        if passed_go:
            self._apply_cash_delta(player, 200, "PASS_GO", events, turn_index=turn_index)
        return target

    def _find_next_index(self, start_index: int, kind: str) -> int:
        board_size = len(self.state.board)
        for offset in range(1, board_size + 1):
            idx = (start_index + offset) % board_size
            if self.state.board[idx].kind == kind:
                return idx
        return start_index

    def _repairs_cost(self, player_id: str, house_cost: int, hotel_cost: int) -> int:
        houses = 0
        hotels = 0
        for space in self.state.board:
            if space.owner_id != player_id:
                continue
            houses += int(space.houses)
            if space.hotel:
                hotels += 1
        return (houses * house_cost) + (hotels * hotel_cost)

    def _return_jail_card(self, player: PlayerState) -> None:
        sources = self._jail_card_sources.get(player.player_id, [])
        deck_type = sources.pop(0) if sources else "CHANCE"
        deck = self._chance_deck if deck_type == "CHANCE" else self._community_chest_deck
        deck.append("GET_OUT_OF_JAIL_FREE")

    def _build_buy_or_auction_decision(self, player: PlayerState, space: SpaceState) -> DecisionPoint:
        decision_id = f"{self.run_id}-dec-{self._decision_seq:06d}"
        self._decision_seq += 1
        legal_actions: list[dict[str, Any]] = []
        if space.price is not None and player.cash >= space.price:
            legal_actions.append(self._build_space_action("buy_property", highlight=[space.index]))
        legal_actions.append(self._build_space_action("start_auction"))
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "decision_id": decision_id,
            "turn_index": self.state.turn_index,
            "player_id": player.player_id,
            "decision_type": "BUY_OR_AUCTION_DECISION",
            "state": self.get_snapshot(),
            "legal_actions": legal_actions,
        }

    def _build_jail_decision(self, player: PlayerState) -> DecisionPoint:
        decision_id = f"{self.run_id}-dec-{self._decision_seq:06d}"
        self._decision_seq += 1
        legal_actions: list[dict[str, Any]] = []
        if player.jail_turns >= 3:
            if player.cash >= JAIL_FINE:
                legal_actions.append(self._build_space_action("pay_jail_fine"))
        else:
            if player.cash >= JAIL_FINE:
                legal_actions.append(self._build_space_action("pay_jail_fine"))
            legal_actions.append(self._build_space_action("roll_for_doubles"))
            if player.get_out_of_jail_cards > 0:
                legal_actions.append(self._build_space_action("use_get_out_of_jail_card"))
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "decision_id": decision_id,
            "turn_index": self.state.turn_index,
            "player_id": player.player_id,
            "decision_type": "JAIL_DECISION",
            "state": self.get_snapshot(),
            "legal_actions": legal_actions,
        }

    def _build_post_turn_action_decision(self, player: PlayerState) -> DecisionPoint:
        decision_id = f"{self.run_id}-dec-{self._decision_seq:06d}"
        self._decision_seq += 1
        options = self._compute_post_turn_options(player)
        legal_actions: list[dict[str, Any]] = [
            self._build_space_action("end_turn"),
        ]
        if options["mortgageable_space_indices"]:
            legal_actions.append(
                self._build_space_action(
                    "mortgage_property",
                    args_schema=self._args_schema_space_key(),
                )
            )
        if options["unmortgageable_space_indices"]:
            legal_actions.append(
                self._build_space_action(
                    "unmortgage_property",
                    args_schema=self._args_schema_space_key(),
                )
            )
        if options["buildable_space_indices"]:
            legal_actions.append(
                self._build_space_action(
                    "build_houses_or_hotel",
                    args_schema=self._args_schema_plan("build_plan"),
                )
            )
        if options["sellable_building_space_indices"]:
            legal_actions.append(
                self._build_space_action(
                    "sell_houses_or_hotel",
                    args_schema=self._args_schema_plan("sell_plan"),
                )
            )
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "decision_id": decision_id,
            "turn_index": self.state.turn_index,
            "player_id": player.player_id,
            "decision_type": "POST_TURN_ACTION_DECISION",
            "state": self.get_snapshot(),
            "post_turn": {"options": options},
            "legal_actions": legal_actions,
        }

    def _build_liquidation_decision(
        self,
        player: PlayerState,
        payment: dict[str, Any],
        *,
        options: dict[str, list[int]],
    ) -> DecisionPoint:
        decision_id = f"{self.run_id}-dec-{self._decision_seq:06d}"
        self._decision_seq += 1
        legal_actions: list[dict[str, Any]] = []
        if options["mortgageable_space_indices"]:
            legal_actions.append(
                self._build_space_action(
                    "mortgage_property",
                    args_schema=self._args_schema_space_key(),
                )
            )
        if options["sellable_building_space_indices"]:
            legal_actions.append(
                self._build_space_action(
                    "sell_houses_or_hotel",
                    args_schema=self._args_schema_plan("sell_plan"),
                )
            )
        legal_actions.append(self._build_space_action("declare_bankruptcy"))
        owed_amount = int(payment.get("amount", 0))
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "decision_id": decision_id,
            "turn_index": self.state.turn_index,
            "player_id": player.player_id,
            "decision_type": "LIQUIDATION_DECISION",
            "state": self.get_snapshot(),
            "liquidation": {
                "owed_amount": owed_amount,
                "owed_to_player_id": payment.get("to_player_id"),
                "reason": payment.get("reason"),
                "shortfall": max(owed_amount - player.cash, 0),
                "options": options,
            },
            "legal_actions": legal_actions,
        }

    def _compute_post_turn_options(self, player: PlayerState) -> dict[str, Any]:
        return {
            "can_trade_with": [
                other.player_id
                for other in self.state.players
                if other.player_id != player.player_id and not other.bankrupt
            ],
            "mortgageable_space_indices": self._mortgageable_space_indices(player),
            "unmortgageable_space_indices": self._unmortgageable_space_indices(player),
            "buildable_space_indices": self._buildable_space_indices(player),
            "sellable_building_space_indices": self._sellable_building_space_indices(player),
        }

    def _compute_liquidation_options(self, player: PlayerState) -> dict[str, list[int]]:
        return {
            "mortgageable_space_indices": self._mortgageable_space_indices(player),
            "sellable_building_space_indices": self._sellable_building_space_indices(player),
        }

    def _maybe_start_post_turn_decision(
        self,
        events: list[Event],
        player: PlayerState,
        *,
        rolled_double: bool,
    ) -> DecisionPoint | None:
        if player.bankrupt:
            self._end_turn(events, player, allow_extra_turn=False)
            return None
        if player.in_jail:
            self._end_turn(events, player, allow_extra_turn=False)
            return None
        decision = self._build_post_turn_action_decision(player)
        self.state.phase = "AWAITING_DECISION"
        self._pending_decision = decision
        self._pending_turn = {
            "player_id": player.player_id,
            "decision_type": "POST_TURN_ACTION_DECISION",
            "rolled_double": rolled_double,
        }
        events.append(
            self._build_event(
                "LLM_DECISION_REQUESTED",
                self._actor_engine(),
                {
                    "decision_id": decision["decision_id"],
                    "player_id": player.player_id,
                    "decision_type": decision["decision_type"],
                },
                turn_index=self.state.turn_index,
            )
        )
        return decision

    def _build_space_action(
        self,
        action_name: str,
        *,
        args_schema: dict[str, Any] | None = None,
        highlight: list[int] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": action_name,
            "args_schema": args_schema
            or {
                "type": "object",
                "additionalProperties": False,
            },
        }
        if highlight:
            payload["ui_hints"] = {"highlight_space_indices": highlight}
        return payload

    @staticmethod
    def _args_schema_space_key() -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["space_key"],
            "properties": {"space_key": {"type": "string"}},
        }

    @staticmethod
    def _args_schema_plan(field_name: str) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [field_name],
            "properties": {
                field_name: {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["space_key", "kind", "count"],
                        "properties": {
                            "space_key": {"type": "string"},
                            "kind": {"type": "string", "enum": ["HOUSE", "HOTEL"]},
                            "count": {"type": "integer", "minimum": 1},
                        },
                    },
                }
            },
        }

    @staticmethod
    def _build_payment_entry(
        amount: int,
        to_player_id: str | None,
        reason: str,
        *,
        kind: str,
        space_index: int | None = None,
    ) -> dict[str, Any]:
        return {
            "amount": int(amount),
            "to_player_id": to_player_id,
            "reason": reason,
            "kind": kind,
            "space_index": space_index,
        }

    def _request_payment(
        self,
        payer: PlayerState,
        payment: dict[str, Any],
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
        remaining_payments: list[dict[str, Any]] | None = None,
    ) -> DecisionPoint | None:
        amount = int(payment.get("amount", 0))
        if amount <= 0:
            return None
        if payer.cash >= amount:
            self._apply_payment(payer, payment, events, turn_index=turn_index)
            if remaining_payments:
                return self._process_payment_queue(
                    payer,
                    remaining_payments,
                    events,
                    turn_index=turn_index,
                    rolled_double=rolled_double,
                )
            return None
        self._pending_payment = {
            "player_id": payer.player_id,
            "payment": payment,
            "remaining_payments": list(remaining_payments or []),
            "rolled_double": rolled_double,
        }
        options = self._compute_liquidation_options(payer)
        return self._build_liquidation_decision(payer, payment, options=options)

    def _process_payment_queue(
        self,
        payer: PlayerState,
        payments: list[dict[str, Any]],
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> DecisionPoint | None:
        queue = list(payments)
        while queue:
            payment = queue.pop(0)
            amount = int(payment.get("amount", 0))
            if amount <= 0:
                continue
            if payer.cash >= amount:
                self._apply_payment(payer, payment, events, turn_index=turn_index)
                continue
            self._pending_payment = {
                "player_id": payer.player_id,
                "payment": payment,
                "remaining_payments": list(queue),
                "rolled_double": rolled_double,
            }
            options = self._compute_liquidation_options(payer)
            return self._build_liquidation_decision(payer, payment, options=options)
        return None

    def _apply_payment(
        self,
        payer: PlayerState,
        payment: dict[str, Any],
        events: list[Event],
        *,
        turn_index: int,
    ) -> None:
        amount = int(payment.get("amount", 0))
        if amount <= 0:
            return
        reason = str(payment.get("reason", "PAYMENT"))
        to_player_id = payment.get("to_player_id")
        self._apply_cash_delta(payer, -amount, reason, events, turn_index=turn_index)
        if to_player_id:
            creditor = self._find_player(str(to_player_id))
            if creditor is not None:
                self._apply_cash_delta(creditor, amount, reason, events, turn_index=turn_index)
        if (
            payment.get("kind") == "RENT"
            and payment.get("space_index") is not None
            and to_player_id
        ):
            space_index = int(payment.get("space_index", 0))
            events.append(
                self._build_event(
                    "RENT_PAID",
                    self._actor_player(payer.player_id),
                    {
                        "from_player_id": payer.player_id,
                        "to_player_id": str(to_player_id),
                        "amount": amount,
                        "space_index": space_index,
                    },
                    turn_index=turn_index,
                )
            )

    def _resolve_pending_payment(
        self,
        payer: PlayerState,
        events: list[Event],
        *,
        turn_index: int,
    ) -> DecisionPoint | None:
        pending = self._pending_payment
        if pending is None:
            return None
        payment = pending.get("payment", {})
        remaining = list(pending.get("remaining_payments", []))
        rolled_double = bool(pending.get("rolled_double", False))
        amount = int(payment.get("amount", 0))
        if payer.cash < amount:
            options = self._compute_liquidation_options(payer)
            if not options["mortgageable_space_indices"] and not options["sellable_building_space_indices"]:
                creditor_id = payment.get("to_player_id")
                creditor = self._find_player(creditor_id) if creditor_id else None
                self._handle_bankruptcy(payer, creditor, events, turn_index=turn_index)
                self._pending_payment = None
                self._end_turn(events, payer, allow_extra_turn=False)
                return None
            decision = self._build_liquidation_decision(payer, payment, options=options)
            self.state.phase = "AWAITING_DECISION"
            self._pending_decision = decision
            self._pending_turn = {
                "player_id": payer.player_id,
                "decision_type": "LIQUIDATION_DECISION",
                "rolled_double": rolled_double,
            }
            events.append(
                self._build_event(
                    "LLM_DECISION_REQUESTED",
                    self._actor_engine(),
                    {
                        "decision_id": decision["decision_id"],
                        "player_id": payer.player_id,
                        "decision_type": decision["decision_type"],
                    },
                    turn_index=turn_index,
                )
            )
            return decision
        self._apply_payment(payer, payment, events, turn_index=turn_index)
        self._pending_payment = None
        decision = self._process_payment_queue(
            payer,
            remaining,
            events,
            turn_index=turn_index,
            rolled_double=rolled_double,
        )
        if decision is not None:
            self.state.phase = "AWAITING_DECISION"
            self._pending_decision = decision
            self._pending_turn = {
                "player_id": payer.player_id,
                "decision_type": "LIQUIDATION_DECISION",
                "rolled_double": rolled_double,
            }
            events.append(
                self._build_event(
                    "LLM_DECISION_REQUESTED",
                    self._actor_engine(),
                    {
                        "decision_id": decision["decision_id"],
                        "player_id": payer.player_id,
                        "decision_type": decision["decision_type"],
                    },
                    turn_index=turn_index,
                )
            )
            return decision
        return self._maybe_start_post_turn_decision(
            events,
            payer,
            rolled_double=rolled_double,
        )

    def _space_index_from_key(self, space_key: str | None) -> int | None:
        if not space_key:
            return None
        normalized = normalize_space_key(str(space_key))
        return SPACE_INDEX_BY_KEY.get(normalized)

    @staticmethod
    def _house_value(space: SpaceState) -> int:
        if space.hotel:
            return HOTEL_HOUSE_EQUIV
        return int(space.houses)

    def _group_has_buildings(self, group: str) -> bool:
        indices = GROUP_INDEXES.get(group, [])
        return any(
            self.state.board[index].houses > 0 or self.state.board[index].hotel for index in indices
        )

    def _group_has_mortgaged(self, group: str) -> bool:
        indices = GROUP_INDEXES.get(group, [])
        return any(self.state.board[index].mortgaged for index in indices)

    @staticmethod
    def _mortgage_value(space: SpaceState) -> int:
        price = space.price or 0
        return price // 2

    def _unmortgage_cost(self, space: SpaceState) -> int:
        value = self._mortgage_value(space)
        return int(math.ceil(value * 1.1))

    def _mortgageable_space_indices(self, player: PlayerState) -> list[int]:
        indices: list[int] = []
        for space in self.state.board:
            if space.owner_id != player.player_id:
                continue
            if space.mortgaged:
                continue
            if space.houses > 0 or space.hotel:
                continue
            if space.group and self._group_has_buildings(space.group):
                continue
            indices.append(space.index)
        return indices

    def _unmortgageable_space_indices(self, player: PlayerState) -> list[int]:
        indices: list[int] = []
        for space in self.state.board:
            if space.owner_id != player.player_id:
                continue
            if not space.mortgaged:
                continue
            cost = self._unmortgage_cost(space)
            if player.cash < cost:
                continue
            indices.append(space.index)
        return indices

    def _buildable_space_indices(self, player: PlayerState) -> list[int]:
        indices: list[int] = []
        for group, group_indices in GROUP_INDEXES.items():
            if group in {"RAILROAD", "UTILITY"}:
                continue
            if not all(self.state.board[index].owner_id == player.player_id for index in group_indices):
                continue
            if self._group_has_mortgaged(group):
                continue
            house_cost = HOUSE_COST_BY_GROUP.get(group, 0)
            if player.cash < house_cost:
                continue
            values = {index: self._house_value(self.state.board[index]) for index in group_indices}
            min_value = min(values.values()) if values else 0
            if min_value >= HOTEL_HOUSE_EQUIV:
                continue
            for index in group_indices:
                space = self.state.board[index]
                value = values[index]
                if value != min_value:
                    continue
                if space.hotel:
                    continue
                if space.houses < HOUSE_LIMIT:
                    if self.state.bank.houses_remaining <= 0:
                        continue
                    indices.append(index)
                elif space.houses == HOUSE_LIMIT:
                    if self.state.bank.hotels_remaining <= 0:
                        continue
                    indices.append(index)
        return indices

    def _sellable_building_space_indices(self, player: PlayerState) -> list[int]:
        indices: list[int] = []
        for group, group_indices in GROUP_INDEXES.items():
            if group in {"RAILROAD", "UTILITY"}:
                continue
            if not all(self.state.board[index].owner_id == player.player_id for index in group_indices):
                continue
            values = {index: self._house_value(self.state.board[index]) for index in group_indices}
            max_value = max(values.values()) if values else 0
            if max_value <= 0:
                continue
            for index in group_indices:
                space = self.state.board[index]
                if values[index] != max_value:
                    continue
                if space.hotel:
                    if self.state.bank.houses_remaining < HOUSE_LIMIT:
                        continue
                    indices.append(index)
                elif space.houses > 0:
                    indices.append(index)
        return indices

    def _apply_mortgage(self, player: PlayerState, action: dict[str, Any], events: list[Event]) -> None:
        args = action.get("args", {})
        space_index = self._space_index_from_key(args.get("space_key"))
        if space_index is None:
            raise ValueError("Unknown space_key for mortgage.")
        space = self.state.board[space_index]
        if space.owner_id != player.player_id:
            raise ValueError("Cannot mortgage unowned property.")
        if space.mortgaged:
            raise ValueError("Property already mortgaged.")
        if space.houses > 0 or space.hotel:
            raise ValueError("Cannot mortgage property with buildings.")
        if space.group and self._group_has_buildings(space.group):
            raise ValueError("Cannot mortgage while group has buildings.")
        value = self._mortgage_value(space)
        space.mortgaged = True
        self._apply_cash_delta(player, value, "MORTGAGE", events, turn_index=self.state.turn_index)
        events.append(
            self._build_event(
                "PROPERTY_MORTGAGED",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "space_index": space_index, "amount": value},
                turn_index=self.state.turn_index,
            )
        )

    def _apply_unmortgage(self, player: PlayerState, action: dict[str, Any], events: list[Event]) -> None:
        args = action.get("args", {})
        space_index = self._space_index_from_key(args.get("space_key"))
        if space_index is None:
            raise ValueError("Unknown space_key for unmortgage.")
        space = self.state.board[space_index]
        if space.owner_id != player.player_id:
            raise ValueError("Cannot unmortgage unowned property.")
        if not space.mortgaged:
            raise ValueError("Property not mortgaged.")
        cost = self._unmortgage_cost(space)
        if player.cash < cost:
            raise ValueError("Insufficient cash to unmortgage.")
        space.mortgaged = False
        self._apply_cash_delta(player, -cost, "UNMORTGAGE", events, turn_index=self.state.turn_index)
        events.append(
            self._build_event(
                "PROPERTY_UNMORTGAGED",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "space_index": space_index, "amount": cost},
                turn_index=self.state.turn_index,
            )
        )

    def _apply_build_plan(self, player: PlayerState, action: dict[str, Any], events: list[Event]) -> None:
        plan = self._parse_plan(action, "build_plan")
        if not plan:
            raise ValueError("Empty build plan.")
        plan_state = self._validate_build_plan(player, plan)
        total_cost = plan_state["total_cost"]
        self.state.bank.houses_remaining += plan_state["bank_houses_delta"]
        self.state.bank.hotels_remaining += plan_state["bank_hotels_delta"]
        if total_cost > 0:
            self._apply_cash_delta(player, -total_cost, "BUILD", events, turn_index=self.state.turn_index)
        for item in plan:
            space = self.state.board[item["space_index"]]
            if item["kind"] == "HOUSE":
                space.houses += item["count"]
                events.append(
                    self._build_event(
                        "HOUSE_BUILT",
                        self._actor_player(player.player_id),
                        {
                            "player_id": player.player_id,
                            "space_index": space.index,
                            "count": item["count"],
                        },
                        turn_index=self.state.turn_index,
                    )
                )
            else:
                space.houses = 0
                space.hotel = True
                events.append(
                    self._build_event(
                        "HOTEL_BUILT",
                        self._actor_player(player.player_id),
                        {
                            "player_id": player.player_id,
                            "space_index": space.index,
                            "count": item["count"],
                        },
                        turn_index=self.state.turn_index,
                    )
                )

    def _apply_sell_plan(self, player: PlayerState, action: dict[str, Any], events: list[Event]) -> None:
        plan = self._parse_plan(action, "sell_plan")
        if not plan:
            raise ValueError("Empty sell plan.")
        plan_state = self._validate_sell_plan(player, plan)
        proceeds = plan_state["total_proceeds"]
        self.state.bank.houses_remaining += plan_state["bank_houses_delta"]
        self.state.bank.hotels_remaining += plan_state["bank_hotels_delta"]
        if proceeds > 0:
            self._apply_cash_delta(player, proceeds, "SELL_BUILDING", events, turn_index=self.state.turn_index)
        for item in plan:
            space = self.state.board[item["space_index"]]
            if item["kind"] == "HOUSE":
                space.houses -= item["count"]
                events.append(
                    self._build_event(
                        "HOUSE_SOLD",
                        self._actor_player(player.player_id),
                        {
                            "player_id": player.player_id,
                            "space_index": space.index,
                            "count": item["count"],
                        },
                        turn_index=self.state.turn_index,
                    )
                )
            else:
                space.hotel = False
                space.houses = HOUSE_LIMIT
                events.append(
                    self._build_event(
                        "HOTEL_SOLD",
                        self._actor_player(player.player_id),
                        {
                            "player_id": player.player_id,
                            "space_index": space.index,
                            "count": item["count"],
                        },
                        turn_index=self.state.turn_index,
                    )
                )

    def _parse_plan(self, action: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
        args = action.get("args", {})
        raw_plan = args.get(field_name)
        if not isinstance(raw_plan, list):
            raise ValueError("Invalid plan payload.")
        plan: list[dict[str, Any]] = []
        for item in raw_plan:
            if not isinstance(item, dict):
                raise ValueError("Invalid plan item.")
            space_key = item.get("space_key")
            kind = item.get("kind")
            count = item.get("count")
            if not isinstance(kind, str):
                raise ValueError("Invalid building kind.")
            if not isinstance(count, int) or count <= 0:
                raise ValueError("Invalid building count.")
            space_index = self._space_index_from_key(space_key)
            if space_index is None:
                raise ValueError("Unknown space_key.")
            plan.append(
                {
                    "space_index": space_index,
                    "kind": kind.upper(),
                    "count": count,
                }
            )
        return plan

    def _validate_build_plan(self, player: PlayerState, plan: list[dict[str, Any]]) -> dict[str, int]:
        temp: dict[int, tuple[int, bool]] = {
            space.index: (space.houses, space.hotel) for space in self.state.board
        }
        bank_houses_delta = 0
        bank_hotels_delta = 0
        total_cost = 0
        touched_groups: set[str] = set()

        for item in plan:
            space = self.state.board[item["space_index"]]
            kind = item["kind"]
            count = item["count"]
            if space.owner_id != player.player_id:
                raise ValueError("Cannot build on unowned property.")
            if space.kind != "PROPERTY" or not space.group or space.group in {"RAILROAD", "UTILITY"}:
                raise ValueError("Invalid build target.")
            if not all(
                self.state.board[index].owner_id == player.player_id
                for index in GROUP_INDEXES.get(space.group, [])
            ):
                raise ValueError("Cannot build without monopoly.")
            if self._group_has_mortgaged(space.group):
                raise ValueError("Cannot build on mortgaged group.")
            house_cost = HOUSE_COST_BY_GROUP.get(space.group, 0)
            houses, hotel = temp[space.index]
            if kind == "HOUSE":
                if hotel:
                    raise ValueError("Cannot build house on hotel.")
                if houses + count > HOUSE_LIMIT:
                    raise ValueError("Too many houses.")
                temp[space.index] = (houses + count, False)
                bank_houses_delta -= count
                total_cost += house_cost * count
            elif kind == "HOTEL":
                if count != 1:
                    raise ValueError("Hotel build count must be 1.")
                if hotel or houses != HOUSE_LIMIT:
                    raise ValueError("Hotel requires four houses.")
                temp[space.index] = (0, True)
                bank_hotels_delta -= 1
                bank_houses_delta += HOUSE_LIMIT
                total_cost += house_cost
            else:
                raise ValueError("Unknown build kind.")
            touched_groups.add(space.group)

        if self.state.bank.houses_remaining + bank_houses_delta < 0:
            raise ValueError("Bank houses exhausted.")
        if self.state.bank.hotels_remaining + bank_hotels_delta < 0:
            raise ValueError("Bank hotels exhausted.")
        if player.cash < total_cost:
            raise ValueError("Insufficient cash to build.")
        for group in touched_groups:
            indices = GROUP_INDEXES.get(group, [])
            values = [
                HOTEL_HOUSE_EQUIV if temp[index][1] else temp[index][0] for index in indices
            ]
            if values and max(values) - min(values) > 1:
                raise ValueError("Uneven building across group.")

        return {
            "bank_houses_delta": bank_houses_delta,
            "bank_hotels_delta": bank_hotels_delta,
            "total_cost": total_cost,
        }

    def _validate_sell_plan(self, player: PlayerState, plan: list[dict[str, Any]]) -> dict[str, int]:
        temp: dict[int, tuple[int, bool]] = {
            space.index: (space.houses, space.hotel) for space in self.state.board
        }
        bank_houses_delta = 0
        bank_hotels_delta = 0
        total_proceeds = 0
        touched_groups: set[str] = set()

        for item in plan:
            space = self.state.board[item["space_index"]]
            kind = item["kind"]
            count = item["count"]
            if space.owner_id != player.player_id:
                raise ValueError("Cannot sell on unowned property.")
            if space.kind != "PROPERTY" or not space.group or space.group in {"RAILROAD", "UTILITY"}:
                raise ValueError("Invalid sell target.")
            house_cost = HOUSE_COST_BY_GROUP.get(space.group, 0)
            houses, hotel = temp[space.index]
            if kind == "HOUSE":
                if hotel:
                    raise ValueError("Cannot sell house from hotel.")
                if houses < count:
                    raise ValueError("Not enough houses to sell.")
                temp[space.index] = (houses - count, False)
                bank_houses_delta += count
                total_proceeds += (house_cost * count) // 2
            elif kind == "HOTEL":
                if count != 1:
                    raise ValueError("Hotel sell count must be 1.")
                if not hotel:
                    raise ValueError("No hotel to sell.")
                temp[space.index] = (HOUSE_LIMIT, False)
                bank_hotels_delta += 1
                bank_houses_delta -= HOUSE_LIMIT
                total_proceeds += house_cost // 2
            else:
                raise ValueError("Unknown sell kind.")
            touched_groups.add(space.group)

        if self.state.bank.houses_remaining + bank_houses_delta < 0:
            raise ValueError("Insufficient bank houses for hotel sale.")
        for group in touched_groups:
            indices = GROUP_INDEXES.get(group, [])
            values = [
                HOTEL_HOUSE_EQUIV if temp[index][1] else temp[index][0] for index in indices
            ]
            if values and max(values) - min(values) > 1:
                raise ValueError("Uneven building across group.")

        return {
            "bank_houses_delta": bank_houses_delta,
            "bank_hotels_delta": bank_hotels_delta,
            "total_proceeds": total_proceeds,
        }

    def _calculate_rent(self, space: SpaceState, owner: PlayerState, dice_total: int) -> int:
        if space.kind == "UTILITY":
            owned = self._count_owned(owner.player_id, "UTILITY")
            multiplier = UTILITY_RENT_MULTIPLIER.get(owned, 4)
            return dice_total * multiplier
        if space.kind == "RAILROAD":
            owned = self._count_owned(owner.player_id, "RAILROAD")
            if owned <= 0:
                return 0
            return RAILROAD_RENTS[min(owned, 4) - 1]
        rent_table = PROPERTY_RENT_TABLES.get(space.index)
        if not rent_table:
            return 0
        if space.hotel:
            return rent_table[5]
        if space.houses > 0:
            return rent_table[space.houses]
        base_rent = rent_table[0]
        if space.group and self._has_monopoly(owner.player_id, space.group):
            base_rent *= 2
        return base_rent

    def _has_monopoly(self, player_id: str, group: str) -> bool:
        if group in {"RAILROAD", "UTILITY"}:
            return False
        indices = GROUP_INDEXES.get(group)
        if not indices:
            return False
        return all(
            self.state.board[index].owner_id == player_id and not self.state.board[index].mortgaged
            for index in indices
        )

    def _count_owned(self, player_id: str, kind: str) -> int:
        return sum(1 for space in self.state.board if space.kind == kind and space.owner_id == player_id)

    def _pay_rent(
        self,
        payer: PlayerState,
        owner: PlayerState,
        amount: int,
        space_index: int,
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> DecisionPoint | None:
        payment = self._build_payment_entry(
            amount,
            owner.player_id,
            "RENT",
            kind="RENT",
            space_index=space_index,
        )
        return self._request_payment(
            payer,
            payment,
            events,
            turn_index=turn_index,
            rolled_double=rolled_double,
        )

    def _pay_tax(
        self,
        payer: PlayerState,
        amount: int,
        reason: str,
        events: list[Event],
        *,
        turn_index: int,
        rolled_double: bool,
    ) -> DecisionPoint | None:
        payment = self._build_payment_entry(amount, None, reason, kind="TAX")
        return self._request_payment(
            payer,
            payment,
            events,
            turn_index=turn_index,
            rolled_double=rolled_double,
        )

    def _handle_bankruptcy(
        self,
        player: PlayerState,
        creditor: PlayerState | None,
        events: list[Event],
        *,
        turn_index: int,
    ) -> None:
        if player.bankrupt:
            return
        remaining_cash = player.cash
        player.bankrupt = True
        player.bankrupt_to = creditor.player_id if creditor else None
        player.doubles_count = 0
        if remaining_cash > 0:
            self._apply_cash_delta(
                player,
                -remaining_cash,
                "BANKRUPTCY_CASH",
                events,
                turn_index=turn_index,
            )
            if creditor is not None:
                self._apply_cash_delta(
                    creditor,
                    remaining_cash,
                    "BANKRUPTCY_CASH",
                    events,
                    turn_index=turn_index,
                )
        events.append(
            self._build_event(
                "CASH_CHANGED",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "delta": 0, "reason": "BANKRUPTCY"},
                turn_index=turn_index,
            )
        )

        for space in self.state.board:
            if space.owner_id != player.player_id:
                continue
            if creditor is not None:
                space.owner_id = creditor.player_id
                events.append(
                    self._build_event(
                        "PROPERTY_PURCHASED",
                        self._actor_player(creditor.player_id),
                        {"player_id": creditor.player_id, "space_index": space.index, "price": 0},
                        turn_index=turn_index,
                    )
                )
            else:
                if space.hotel:
                    self.state.bank.hotels_remaining += 1
                if space.houses > 0:
                    self.state.bank.houses_remaining += space.houses
                space.owner_id = None
                space.mortgaged = False
                space.houses = 0
                space.hotel = False
        if creditor is None:
            events.append(
                self._build_event(
                    "CASH_CHANGED",
                    self._actor_player(player.player_id),
                    {"player_id": player.player_id, "delta": 0, "reason": "BANKRUPTCY_ASSETS_TO_BANK"},
                    turn_index=turn_index,
                )
            )

    def _apply_property_purchase(
        self,
        player: PlayerState,
        space: SpaceState,
        events: list[Event],
    ) -> None:
        if space.owner_id is not None:
            raise ValueError("Property is already owned.")
        price = space.price or 0
        if player.cash < price:
            raise ValueError("Insufficient cash to buy property.")
        player.cash -= price
        space.owner_id = player.player_id
        events.append(
            self._build_event(
                "PROPERTY_PURCHASED",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "space_index": space.index, "price": price},
                turn_index=self.state.turn_index,
            )
        )
        events.append(
            self._build_event(
                "CASH_CHANGED",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "delta": -price, "reason": "buy_property"},
                turn_index=self.state.turn_index,
            )
        )

    def _apply_cash_delta(
        self,
        player: PlayerState,
        delta: int,
        reason: str,
        events: list[Event],
        *,
        turn_index: int,
    ) -> None:
        player.cash += delta
        events.append(
            self._build_event(
                "CASH_CHANGED",
                self._actor_player(player.player_id),
                {"player_id": player.player_id, "delta": delta, "reason": reason},
                turn_index=turn_index,
            )
        )

    def _end_turn(self, events: list[Event], player: PlayerState, *, allow_extra_turn: bool) -> None:
        self.state.phase = "END_TURN"
        events.append(self._build_event("TURN_ENDED", self._actor_engine(), {}, turn_index=self.state.turn_index))
        self.state.turn_index += 1
        if allow_extra_turn:
            next_player_id = player.player_id
        else:
            next_player_id = self._next_active_player_id(player.player_id)
        self.state.active_player_id = next_player_id
        self.state.phase = "START_TURN"

    def _should_end_game(self) -> bool:
        if self._stop_reason is not None:
            return True
        if self.state.turn_index >= self._max_turns:
            self._stop_reason = "TURN_LIMIT"
            return True
        if self._active_player_count() <= 1 and self.state.players:
            self._stop_reason = "BANKRUPTCY"
            return True
        return False

    def _finish_game(self, events: list[Event]) -> None:
        if self.state.phase == "GAME_OVER":
            return
        winner_id = self._determine_winner()
        self.state.phase = "GAME_OVER"
        self.state.active_player_id = winner_id
        events.append(
            self._build_event(
                "GAME_ENDED",
                self._actor_engine(),
                {"winner_player_id": winner_id, "reason": self._stop_reason or "TURN_LIMIT"},
                turn_index=max(self.state.turn_index, 0),
            )
        )

    def _current_player(self) -> PlayerState:
        player = self._find_player(self.state.active_player_id)
        return player or self.state.players[0]

    def _find_player(self, player_id: str) -> PlayerState | None:
        for player in self.state.players:
            if player.player_id == player_id:
                return player
        return None

    def _next_active_player_id(self, current_id: str) -> str:
        if not self.state.players:
            return ""
        try:
            start_index = next(
                idx for idx, player in enumerate(self.state.players) if player.player_id == current_id
            )
        except StopIteration:
            start_index = 0
        for offset in range(1, len(self.state.players) + 1):
            candidate = self.state.players[(start_index + offset) % len(self.state.players)]
            if not candidate.bankrupt:
                return candidate.player_id
        return current_id

    def _active_player_count(self) -> int:
        return sum(1 for player in self.state.players if not player.bankrupt)

    def _determine_winner(self) -> str:
        active_players = [player for player in self.state.players if not player.bankrupt]
        if active_players:
            winner = max(active_players, key=lambda player: player.cash)
            return winner.player_id
        winner = max(self.state.players, key=lambda player: player.cash)
        return winner.player_id

    def _validate_action(self, action: dict[str, Any], decision: DecisionPoint) -> str | None:
        if action.get("schema_version") != "v1":
            return "Invalid schema_version"
        if action.get("decision_id") != decision["decision_id"]:
            return "Decision id mismatch"
        allowed = {entry["action"] for entry in decision.get("legal_actions", [])}
        if action.get("action") not in allowed:
            return "Action not legal for decision"
        if action.get("action") in {"buy_property", "start_auction"}:
            space_index = self._pending_turn.get("space_index")
            if space_index is None:
                return "Missing pending space_index"
        if action.get("action") in {"mortgage_property", "unmortgage_property"}:
            args = action.get("args")
            if not isinstance(args, dict) or "space_key" not in args:
                return "Missing space_key"
        if action.get("action") == "build_houses_or_hotel":
            args = action.get("args")
            if not isinstance(args, dict) or "build_plan" not in args:
                return "Missing build_plan"
        if action.get("action") == "sell_houses_or_hotel":
            args = action.get("args")
            if not isinstance(args, dict) or "sell_plan" not in args:
                return "Missing sell_plan"
        return None

    def _build_event(
        self,
        event_type: str,
        actor: dict[str, Any],
        payload: dict[str, Any],
        *,
        turn_index: int,
    ) -> Event:
        seq = self._seq
        ts_ms = self._start_ts_ms + (self._seq * self._ts_step_ms)
        self._seq += 1
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "event_id": f"{self.run_id}-evt-{seq:06d}",
            "seq": seq,
            "turn_index": turn_index,
            "ts_ms": ts_ms,
            "actor": actor,
            "type": event_type,
            "payload": payload,
        }

    @staticmethod
    def _actor_engine() -> dict[str, Any]:
        return {"kind": "ENGINE", "player_id": None}

    @staticmethod
    def _actor_player(player_id: str) -> dict[str, Any]:
        return {"kind": "PLAYER", "player_id": player_id}


def create_initial_state(
    run_id: str,
    seed: int,
    players: list[dict[str, Any]],
) -> GameState:
    player_state: list[PlayerState] = [
        PlayerState(player_id=player["player_id"], name=player["name"]) for player in players
    ]
    active_player_id = player_state[0].player_id if player_state else ""
    return GameState(
        run_id=run_id,
        seed=seed,
        turn_index=0,
        phase="START_TURN",
        active_player_id=active_player_id,
        players=player_state,
        bank=BankState(),
        board=build_board(),
    )


def advance_until_decision(engine: Engine, max_steps: int = 1) -> StepResult:
    return engine.advance_until_decision(max_steps=max_steps)
