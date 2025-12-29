from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Iterable

from monopoly_engine import Engine, create_initial_state as engine_create_initial_state


def create_initial_state(
    run_id: str,
    players: list[dict[str, Any]],
    *,
    seed: int = 0,
) -> dict[str, Any]:
    return engine_create_initial_state(run_id, seed, players).to_snapshot()


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
        max_turns: int = 200,
        event_delay_s: float = 0.25,
        start_ts_ms: int = 0,
        ts_step_ms: int = 250,
    ) -> None:
        self.run_id = run_id
        self._engine = Engine(
            seed=seed,
            players=players,
            run_id=run_id,
            max_turns=max_turns,
            start_ts_ms=start_ts_ms,
            ts_step_ms=ts_step_ms,
        )
        self._event_delay_s = event_delay_s

    def request_stop(self, reason: str = "STOPPED") -> None:
        self._engine.request_stop(reason)

    def get_snapshot(self) -> dict[str, Any]:
        return self._engine.get_snapshot()

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
            if on_snapshot is not None and event["type"] in {
                "LLM_DECISION_REQUESTED",
                "TURN_ENDED",
                "GAME_ENDED",
            }:
                await on_snapshot(self.get_snapshot())
            if self._event_delay_s > 0:
                await asyncio.sleep(self._event_delay_s)
        if on_summary is not None:
            await on_summary(self._engine.build_summary())

    def _event_stream(self) -> Iterable[dict[str, Any]]:
        while True:
            _, events, decision, _ = self._engine.advance_until_decision(max_steps=1)
            if not events and decision is None:
                break
            for event in events:
                yield event
            if decision is not None:
                action = self._choose_action(decision)
                _, action_events, _, _ = self._engine.apply_action(action)
                for event in action_events:
                    yield event
                if self._engine.is_game_over():
                    break
                continue
            if self._engine.is_game_over():
                break

    @staticmethod
    def _choose_action(decision: dict[str, Any]) -> dict[str, Any]:
        legal_actions = [entry["action"] for entry in decision.get("legal_actions", [])]
        if decision.get("decision_type") == "AUCTION_BID_DECISION":
            auction = decision.get("state", {}).get("auction", {})
            current_high_bid = int(auction.get("current_high_bid", 0) or 0)
            min_next_bid = current_high_bid + 1
            player_cash = None
            for player in decision.get("state", {}).get("players", []):
                if player.get("player_id") == decision.get("player_id"):
                    player_cash = int(player.get("cash", 0))
                    break
            if "bid_auction" in legal_actions and player_cash is not None and player_cash >= min_next_bid:
                return {
                    "schema_version": "v1",
                    "decision_id": decision["decision_id"],
                    "action": "bid_auction",
                    "args": {"bid_amount": min_next_bid},
                }
            if "drop_out" in legal_actions:
                return {
                    "schema_version": "v1",
                    "decision_id": decision["decision_id"],
                    "action": "drop_out",
                    "args": {},
                }
        if decision.get("decision_type") == "TRADE_RESPONSE_DECISION":
            if "reject_trade" in legal_actions:
                return {
                    "schema_version": "v1",
                    "decision_id": decision["decision_id"],
                    "action": "reject_trade",
                    "args": {},
                }
            if "accept_trade" in legal_actions:
                return {
                    "schema_version": "v1",
                    "decision_id": decision["decision_id"],
                    "action": "accept_trade",
                    "args": {},
                }
        if "buy_property" in legal_actions:
            action_name = "buy_property"
        elif "start_auction" in legal_actions:
            action_name = "start_auction"
        elif "end_turn" in legal_actions:
            action_name = "end_turn"
        elif "declare_bankruptcy" in legal_actions:
            action_name = "declare_bankruptcy"
        elif legal_actions:
            action_name = legal_actions[0]
        else:
            action_name = "NOOP"
        args: dict[str, Any] = {}
        if action_name == "NOOP":
            args = {"reason": "mock"}
        return {
            "schema_version": "v1",
            "decision_id": decision["decision_id"],
            "action": action_name,
            "args": args,
        }
