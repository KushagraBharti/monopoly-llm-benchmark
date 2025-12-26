from __future__ import annotations

import asyncio
import copy
import random
from typing import Any, Awaitable, Callable, Iterable


BOARD_SPEC = [
    (0, "GO", "Go", None, None),
    (1, "PROPERTY", "Mediterranean Avenue", "BROWN", 60),
    (2, "COMMUNITY_CHEST", "Community Chest", None, None),
    (3, "PROPERTY", "Baltic Avenue", "BROWN", 60),
    (4, "TAX", "Income Tax", None, None),
    (5, "RAILROAD", "Reading Railroad", "RAILROAD", 200),
    (6, "PROPERTY", "Oriental Avenue", "LIGHT_BLUE", 100),
    (7, "CHANCE", "Chance", None, None),
    (8, "PROPERTY", "Vermont Avenue", "LIGHT_BLUE", 100),
    (9, "PROPERTY", "Connecticut Avenue", "LIGHT_BLUE", 120),
    (10, "JAIL", "Jail", None, None),
    (11, "PROPERTY", "St. Charles Place", "PINK", 140),
    (12, "UTILITY", "Electric Company", "UTILITY", 150),
    (13, "PROPERTY", "States Avenue", "PINK", 140),
    (14, "PROPERTY", "Virginia Avenue", "PINK", 160),
    (15, "RAILROAD", "Pennsylvania Railroad", "RAILROAD", 200),
    (16, "PROPERTY", "St. James Place", "ORANGE", 180),
    (17, "COMMUNITY_CHEST", "Community Chest", None, None),
    (18, "PROPERTY", "Tennessee Avenue", "ORANGE", 180),
    (19, "PROPERTY", "New York Avenue", "ORANGE", 200),
    (20, "FREE_PARKING", "Free Parking", None, None),
    (21, "PROPERTY", "Kentucky Avenue", "RED", 220),
    (22, "CHANCE", "Chance", None, None),
    (23, "PROPERTY", "Indiana Avenue", "RED", 220),
    (24, "PROPERTY", "Illinois Avenue", "RED", 240),
    (25, "RAILROAD", "B. & O. Railroad", "RAILROAD", 200),
    (26, "PROPERTY", "Atlantic Avenue", "YELLOW", 260),
    (27, "PROPERTY", "Ventnor Avenue", "YELLOW", 260),
    (28, "UTILITY", "Water Works", "UTILITY", 150),
    (29, "PROPERTY", "Marvin Gardens", "YELLOW", 280),
    (30, "GO_TO_JAIL", "Go To Jail", None, None),
    (31, "PROPERTY", "Pacific Avenue", "GREEN", 300),
    (32, "PROPERTY", "North Carolina Avenue", "GREEN", 300),
    (33, "COMMUNITY_CHEST", "Community Chest", None, None),
    (34, "PROPERTY", "Pennsylvania Avenue", "GREEN", 320),
    (35, "RAILROAD", "Short Line", "RAILROAD", 200),
    (36, "CHANCE", "Chance", None, None),
    (37, "PROPERTY", "Park Place", "DARK_BLUE", 350),
    (38, "TAX", "Luxury Tax", None, None),
    (39, "PROPERTY", "Boardwalk", "DARK_BLUE", 400),
]

BUYABLE_KINDS = {"PROPERTY", "RAILROAD", "UTILITY"}
DEFAULT_STARTING_CASH = 1500


def build_board() -> list[dict[str, Any]]:
    board = []
    for index, kind, name, group, price in BOARD_SPEC:
        board.append(
            {
                "index": index,
                "kind": kind,
                "name": name,
                "group": group,
                "price": price,
                "owner_id": None,
                "mortgaged": False,
                "houses": 0,
                "hotel": False,
            }
        )
    return board


def create_initial_state(run_id: str, players: list[dict[str, Any]]) -> dict[str, Any]:
    player_state = []
    for player in players:
        player_state.append(
            {
                "player_id": player["player_id"],
                "name": player["name"],
                "cash": DEFAULT_STARTING_CASH,
                "position": 0,
                "in_jail": False,
                "jail_turns": 0,
                "doubles_count": 0,
                "bankrupt": False,
                "bankrupt_to": None,
                "get_out_of_jail_cards": 0,
            }
        )
    return {
        "schema_version": "v1",
        "run_id": run_id,
        "turn_index": 0,
        "phase": "START_TURN",
        "active_player_id": player_state[0]["player_id"],
        "players": player_state,
        "bank": {"houses_remaining": 32, "hotels_remaining": 12},
        "board": build_board(),
    }


def build_idle_snapshot() -> dict[str, Any]:
    snapshot = create_initial_state("idle", [{"player_id": "idle", "name": "Waiting"}])
    snapshot["phase"] = "GAME_OVER"
    snapshot["active_player_id"] = "idle"
    return snapshot


class MockRunner:
    def __init__(
        self,
        seed: int,
        players: list[dict[str, Any]],
        run_id: str,
        *,
        max_turns: int = 30,
        event_delay_s: float = 0.25,
        start_ts_ms: int = 0,
        ts_step_ms: int = 250,
    ) -> None:
        self.run_id = run_id
        self._rng = random.Random(seed)
        self._state = create_initial_state(run_id, players)
        self._player_by_id = {p["player_id"]: p for p in self._state["players"]}
        self._turn_index = 0
        self._seq = 0
        self._max_turns = max_turns
        self._event_delay_s = event_delay_s
        self._start_ts_ms = start_ts_ms
        self._ts_step_ms = ts_step_ms
        self._stop_reason: str | None = None

    def request_stop(self, reason: str = "STOPPED") -> None:
        self._stop_reason = reason

    def get_snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def generate_events(self, limit: int | None = None) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for event in self._event_stream():
            events.append(event)
            if limit is not None and len(events) >= limit:
                break
        return events

    async def run(
        self,
        on_event: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_snapshot: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_summary: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        for event in self._event_stream():
            if on_event is not None:
                await on_event(event)
            if on_snapshot is not None and event["type"] in {"TURN_ENDED", "GAME_ENDED"}:
                await on_snapshot(self.get_snapshot())
            if self._event_delay_s > 0:
                await asyncio.sleep(self._event_delay_s)
        if on_summary is not None:
            await on_summary(self._build_summary())

    def _event_stream(self) -> Iterable[dict[str, Any]]:
        yield self._build_event("GAME_STARTED", self._actor_engine(), {}, turn_index=0)
        while self._turn_index < self._max_turns and self._stop_reason is None:
            yield from self._run_turn_events()
        reason = self._stop_reason or "TURN_LIMIT"
        winner_id = self._determine_winner()
        self._state["phase"] = "GAME_OVER"
        self._state["active_player_id"] = winner_id
        yield self._build_event(
            "GAME_ENDED",
            self._actor_engine(),
            {"winner_player_id": winner_id, "reason": reason},
            turn_index=max(self._turn_index, 0),
        )

    def _run_turn_events(self) -> Iterable[dict[str, Any]]:
        turn_index = self._turn_index
        players = self._state["players"]
        current_player = players[turn_index % len(players)]
        current_id = current_player["player_id"]
        self._state["turn_index"] = turn_index
        self._state["active_player_id"] = current_id
        self._state["phase"] = "START_TURN"

        yield self._build_event("TURN_STARTED", self._actor_engine(), {}, turn_index=turn_index)

        d1 = self._rng.randint(1, 6)
        d2 = self._rng.randint(1, 6)
        self._state["phase"] = "RESOLVING_MOVE"
        yield self._build_event(
            "DICE_ROLLED",
            self._actor_player(current_id),
            {"d1": d1, "d2": d2, "is_double": d1 == d2},
            turn_index=turn_index,
        )

        from_pos = current_player["position"]
        to_pos = (from_pos + d1 + d2) % 40
        passed_go = to_pos < from_pos
        current_player["position"] = to_pos
        yield self._build_event(
            "PLAYER_MOVED",
            self._actor_player(current_id),
            {"from": from_pos, "to": to_pos, "passed_go": passed_go},
            turn_index=turn_index,
        )

        if passed_go:
            current_player["cash"] += 200
            yield self._build_event(
                "CASH_CHANGED",
                self._actor_player(current_id),
                {"player_id": current_id, "delta": 200, "reason": "PASS_GO"},
                turn_index=turn_index,
            )

        space = self._state["board"][to_pos]
        if space["kind"] in BUYABLE_KINDS and space["owner_id"] is None:
            price = space["price"]
            if price is not None and self._rng.random() < 0.3 and current_player["cash"] >= price:
                space["owner_id"] = current_id
                current_player["cash"] -= price
                yield self._build_event(
                    "PROPERTY_PURCHASED",
                    self._actor_player(current_id),
                    {"player_id": current_id, "space_index": to_pos, "price": price},
                    turn_index=turn_index,
                )
                yield self._build_event(
                    "CASH_CHANGED",
                    self._actor_player(current_id),
                    {"player_id": current_id, "delta": -price, "reason": "PURCHASE"},
                    turn_index=turn_index,
                )
        elif space["owner_id"] is not None and space["owner_id"] != current_id:
            price = space["price"]
            owner_id = space["owner_id"]
            if price is not None and owner_id in self._player_by_id:
                rent = max(1, int(price * 0.1))
                owner = self._player_by_id[owner_id]
                current_player["cash"] -= rent
                owner["cash"] += rent
                yield self._build_event(
                    "RENT_PAID",
                    self._actor_player(current_id),
                    {
                        "from_player_id": current_id,
                        "to_player_id": owner_id,
                        "amount": rent,
                        "space_index": to_pos,
                    },
                    turn_index=turn_index,
                )
                yield self._build_event(
                    "CASH_CHANGED",
                    self._actor_player(current_id),
                    {"player_id": current_id, "delta": -rent, "reason": "RENT"},
                    turn_index=turn_index,
                )
                yield self._build_event(
                    "CASH_CHANGED",
                    self._actor_player(owner_id),
                    {"player_id": owner_id, "delta": rent, "reason": "RENT"},
                    turn_index=turn_index,
                )

        self._state["phase"] = "END_TURN"
        yield self._build_event("TURN_ENDED", self._actor_engine(), {}, turn_index=turn_index)

        self._turn_index += 1
        next_player = players[self._turn_index % len(players)]
        self._state["turn_index"] = self._turn_index
        self._state["active_player_id"] = next_player["player_id"]
        self._state["phase"] = "START_TURN"

    def _build_event(
        self,
        event_type: str,
        actor: dict[str, Any],
        payload: dict[str, Any],
        *,
        turn_index: int,
    ) -> dict[str, Any]:
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

    def _determine_winner(self) -> str:
        players = self._state["players"]
        winner = max(players, key=lambda player: player["cash"])
        return winner["player_id"]

    def _build_summary(self) -> dict[str, Any]:
        winner_id = self._determine_winner()
        return {
            "run_id": self.run_id,
            "winner_player_id": winner_id,
            "turn_count": self._turn_index,
            "reason": self._stop_reason or "TURN_LIMIT",
        }

    @staticmethod
    def _actor_engine() -> dict[str, Any]:
        return {"kind": "ENGINE", "player_id": None}

    @staticmethod
    def _actor_player(player_id: str) -> dict[str, Any]:
        return {"kind": "PLAYER", "player_id": player_id}
