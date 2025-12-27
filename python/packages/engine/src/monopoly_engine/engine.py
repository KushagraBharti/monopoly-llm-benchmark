from __future__ import annotations

from typing import Any

from .board import (
    GROUP_INDEXES,
    OWNABLE_KINDS,
    PROPERTY_RENT_TABLES,
    RAILROAD_RENTS,
    TAX_AMOUNTS,
    UTILITY_RENT_MULTIPLIER,
    build_board,
)
from .models import BankState, GameState, PlayerState, SpaceState
from .rng import DeterministicRng

DecisionPoint = dict[str, Any]
Event = dict[str, Any]
StepResult = tuple[GameState, list[Event], DecisionPoint | None, dict[str, Any] | None]


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
        self.state = create_initial_state(run_id, seed, players)

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
                    {"player_id": player_id, "message": action["public_message"]},
                    turn_index=self.state.turn_index,
                )
            )
        if "private_thought" in action:
            events.append(
                self._build_event(
                    "LLM_PRIVATE_THOUGHT",
                    self._actor_player(player_id),
                    {"player_id": player_id, "thought": action["private_thought"]},
                    turn_index=self.state.turn_index,
                )
            )

        action_name = action["action"]
        space_index = action.get("args", {}).get("space_index")
        player = self._find_player(player_id)
        if player is None:
            raise ValueError(f"Unknown player for decision: {player_id}")

        if action_name == "BUY_PROPERTY":
            if space_index is None:
                raise ValueError("Missing space_index for BUY_PROPERTY.")
            space = self.state.board[space_index]
            self._apply_property_purchase(player, space, events)
        elif action_name in {"START_AUCTION", "DECLINE_PROPERTY"}:
            pass
        else:
            raise ValueError(f"Unsupported action: {action_name}")

        self._pending_decision = None
        self._pending_turn = None

        rolled_double = bool(pending_turn.get("rolled_double", False))
        self._end_turn(events, player, allow_extra_turn=rolled_double and not player.bankrupt)
        snapshot = self.get_snapshot()
        if self._should_end_game():
            self._finish_game(events)
            snapshot = self.get_snapshot()
        return self.state, events, None, snapshot

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
            current_player.doubles_count = 0
            events.append(
                self._build_event(
                    "SENT_TO_JAIL",
                    self._actor_player(current_id),
                    {"player_id": current_id, "reason": "THREE_DOUBLES_PENDING"},
                    turn_index=turn_index,
                )
            )
            self._end_turn(events, current_player, allow_extra_turn=False)
            return events, None

        from_pos = current_player.position
        board_size = len(self.state.board)
        to_pos = (from_pos + d1 + d2) % board_size
        passed_go = to_pos < from_pos
        current_player.position = to_pos
        events.append(
            self._build_event(
                "PLAYER_MOVED",
                self._actor_player(current_id),
                {"from": from_pos, "to": to_pos, "passed_go": passed_go},
                turn_index=turn_index,
            )
        )

        if passed_go:
            self._apply_cash_delta(current_player, 200, "PASS_GO", events, turn_index=turn_index)

        space = self.state.board[to_pos]
        decision = self._resolve_landing(current_player, space, d1 + d2, events, turn_index=turn_index)
        if decision is not None:
            self.state.phase = "AWAITING_DECISION"
            self._pending_decision = decision
            self._pending_turn = {
                "rolled_double": is_double,
                "space_index": space.index,
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

        self._end_turn(events, current_player, allow_extra_turn=is_double and not current_player.bankrupt)
        return events, None

    def _resolve_landing(
        self,
        player: PlayerState,
        space: SpaceState,
        dice_total: int,
        events: list[Event],
        *,
        turn_index: int,
    ) -> DecisionPoint | None:
        if space.kind in OWNABLE_KINDS:
            if space.owner_id is None:
                self.state.phase = "AWAITING_DECISION"
                return self._build_buy_decision(player, space)
            if space.owner_id == player.player_id:
                return None
            owner = self._find_player(space.owner_id)
            if owner is None or owner.bankrupt or space.mortgaged:
                return None
            rent = self._calculate_rent(space, owner, dice_total)
            if rent > 0:
                self._pay_rent(player, owner, rent, space.index, events, turn_index=turn_index)
            return None
        if space.kind == "TAX":
            amount = TAX_AMOUNTS.get(space.index, 0)
            if amount > 0:
                reason = "TAX_INCOME" if space.index == 4 else "TAX_LUXURY"
                self._pay_tax(player, amount, reason, events, turn_index=turn_index)
            return None
        if space.kind == "GO_TO_JAIL":
            events.append(
                self._build_event(
                    "SENT_TO_JAIL",
                    self._actor_player(player.player_id),
                    {"player_id": player.player_id, "reason": "GO_TO_JAIL_PENDING"},
                    turn_index=turn_index,
                )
            )
        return None

    def _build_buy_decision(self, player: PlayerState, space: SpaceState) -> DecisionPoint:
        decision_id = f"{self.run_id}-dec-{self._decision_seq:06d}"
        self._decision_seq += 1
        legal_actions: list[dict[str, Any]] = []
        if space.price is not None and player.cash >= space.price:
            legal_actions.append(self._build_space_action("BUY_PROPERTY", space.index, highlight=[space.index]))
        legal_actions.append(self._build_space_action("START_AUCTION", space.index))
        return {
            "schema_version": "v1",
            "run_id": self.run_id,
            "decision_id": decision_id,
            "turn_index": self.state.turn_index,
            "player_id": player.player_id,
            "decision_type": "BUY_DECISION",
            "state": self.get_snapshot(),
            "legal_actions": legal_actions,
        }

    def _build_space_action(
        self,
        action_name: str,
        space_index: int,
        *,
        highlight: list[int] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": action_name,
            "args_schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["space_index"],
                "properties": {
                    "space_index": {"type": "integer", "minimum": 0, "maximum": 39},
                },
            },
        }
        if highlight:
            payload["ui_hints"] = {"highlight_space_indices": highlight}
        return payload

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
        return all(self.state.board[index].owner_id == player_id for index in indices)

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
    ) -> None:
        paid = min(payer.cash, amount)
        if paid > 0:
            self._apply_cash_delta(payer, -paid, "RENT", events, turn_index=turn_index)
            self._apply_cash_delta(owner, paid, "RENT", events, turn_index=turn_index)
            events.append(
                self._build_event(
                    "RENT_PAID",
                    self._actor_player(payer.player_id),
                    {
                        "from_player_id": payer.player_id,
                        "to_player_id": owner.player_id,
                        "amount": paid,
                        "space_index": space_index,
                    },
                    turn_index=turn_index,
                )
            )
        if paid < amount:
            self._handle_bankruptcy(payer, owner, events, turn_index=turn_index)

    def _pay_tax(
        self,
        payer: PlayerState,
        amount: int,
        reason: str,
        events: list[Event],
        *,
        turn_index: int,
    ) -> None:
        paid = min(payer.cash, amount)
        if paid > 0:
            self._apply_cash_delta(payer, -paid, reason, events, turn_index=turn_index)
        if paid < amount:
            self._handle_bankruptcy(payer, None, events, turn_index=turn_index)

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
        player.bankrupt = True
        player.bankrupt_to = creditor.player_id if creditor else None
        player.cash = 0
        player.doubles_count = 0
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
                space.owner_id = None
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
                {"player_id": player.player_id, "delta": -price, "reason": "BUY_PROPERTY"},
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
        if action.get("action") in {"BUY_PROPERTY", "START_AUCTION", "DECLINE_PROPERTY"}:
            space_index = action.get("args", {}).get("space_index")
            if space_index is None:
                return "Missing space_index"
            if space_index != self._pending_turn.get("space_index"):
                return "space_index mismatch"
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
