from __future__ import annotations

from typing import Any

from .board import build_board
from .models import BankState, GameState, PlayerState
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
            return self.state, events, None, snapshot

        if not self._started:
            events.append(self._build_event("GAME_STARTED", self._actor_engine(), {}, turn_index=0))
            self._started = True

        if self.is_game_over():
            return self.state, events, None, snapshot

        steps = 0
        while steps < max_steps and not self.is_game_over():
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
                break
            events.extend(self._run_turn_events())
            snapshot = self.get_snapshot()
            steps += 1
            if self._should_end_game():
                self._finish_game(events)
                snapshot = self.get_snapshot()
                break

        return self.state, events, None, snapshot

    def build_summary(self) -> dict[str, Any]:
        winner_id = self._determine_winner()
        return {
            "run_id": self.run_id,
            "winner_player_id": winner_id,
            "turn_count": self.state.turn_index,
            "reason": self._stop_reason or "TURN_LIMIT",
        }

    def _run_turn_events(self) -> list[Event]:
        events: list[Event] = []
        turn_index = self.state.turn_index
        current_player = self._current_player()
        current_id = current_player.player_id

        self.state.phase = "START_TURN"
        self.state.active_player_id = current_id
        events.append(self._build_event("TURN_STARTED", self._actor_engine(), {}, turn_index=turn_index))

        d1, d2 = self._rng.roll_dice()
        self.state.phase = "RESOLVING_MOVE"
        events.append(
            self._build_event(
                "DICE_ROLLED",
                self._actor_player(current_id),
                {"d1": d1, "d2": d2, "is_double": d1 == d2},
                turn_index=turn_index,
            )
        )

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
            current_player.cash += 200
            events.append(
                self._build_event(
                    "CASH_CHANGED",
                    self._actor_player(current_id),
                    {"player_id": current_id, "delta": 200, "reason": "PASS_GO"},
                    turn_index=turn_index,
                )
            )

        self.state.phase = "END_TURN"
        events.append(self._build_event("TURN_ENDED", self._actor_engine(), {}, turn_index=turn_index))

        self.state.turn_index += 1
        next_player = self._current_player()
        self.state.active_player_id = next_player.player_id
        self.state.phase = "START_TURN"
        return events

    def _should_end_game(self) -> bool:
        return self._stop_reason is not None or self.state.turn_index >= self._max_turns

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
        index = self.state.turn_index % len(self.state.players)
        return self.state.players[index]

    def _determine_winner(self) -> str:
        winner = max(self.state.players, key=lambda player: player.cash)
        return winner.player_id

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
