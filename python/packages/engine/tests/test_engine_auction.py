from __future__ import annotations

from typing import Any

from monopoly_engine import Engine
from monopoly_engine.board import SPACE_KEY_BY_INDEX


def _start_auction(engine: Engine, *, target_index: int = 14) -> dict[str, Any]:
    engine.state.players[0].position = 10
    engine.state.active_player_id = "p1"
    engine._rng.roll_dice = lambda: (1, 3)
    engine.state.board[target_index].owner_id = None
    _, _, decision, _ = engine.advance_until_decision(max_steps=1)
    assert decision is not None
    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "start_auction",
        "args": {},
    }
    _, events, auction_decision, _ = engine.apply_action(action)
    assert auction_decision is not None
    return {
        "events": events,
        "decision": auction_decision,
        "target_index": target_index,
    }


def test_auction_start_creates_state() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
    ]
    engine = Engine(seed=41, players=players, run_id="run-auction-start", max_turns=3, ts_step_ms=1)
    result = _start_auction(engine)

    assert engine.state.auction is not None
    auction = engine.state.auction
    assert auction.property_space_key == SPACE_KEY_BY_INDEX[result["target_index"]]
    assert auction.initiator_player_id == "p1"
    assert auction.active_bidders_player_ids[0] == "p2"
    assert any(event["type"] == "AUCTION_STARTED" for event in result["events"])
    assert result["decision"]["decision_type"] == "AUCTION_BID_DECISION"


def test_auction_bid_updates_high_bid() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
    ]
    engine = Engine(seed=42, players=players, run_id="run-auction-bid", max_turns=3, ts_step_ms=1)
    result = _start_auction(engine)
    decision = result["decision"]

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "bid_auction",
        "args": {"bid_amount": 5},
    }
    _, events, next_decision, _ = engine.apply_action(action)

    assert engine.state.auction is not None
    auction = engine.state.auction
    assert auction.current_high_bid == 5
    assert auction.current_leader_player_id == "p2"
    assert any(event["type"] == "AUCTION_BID_PLACED" for event in events)
    assert next_decision is not None
    assert next_decision["player_id"] == "p3"


def test_auction_drop_removes_bidder() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
        {"player_id": "p3", "name": "P3"},
    ]
    engine = Engine(seed=43, players=players, run_id="run-auction-drop", max_turns=3, ts_step_ms=1)
    result = _start_auction(engine)
    decision = result["decision"]

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "drop_out",
        "args": {},
    }
    _, events, next_decision, _ = engine.apply_action(action)

    assert engine.state.auction is not None
    auction = engine.state.auction
    assert "p2" not in auction.active_bidders_player_ids
    assert any(event["type"] == "AUCTION_PLAYER_DROPPED" for event in events)
    assert next_decision is not None
    assert next_decision["decision_type"] == "AUCTION_BID_DECISION"


def test_auction_end_sold() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=44, players=players, run_id="run-auction-sold", max_turns=3, ts_step_ms=1)
    result = _start_auction(engine)
    target_index = result["target_index"]
    decision = result["decision"]

    bid_action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "bid_auction",
        "args": {"bid_amount": 10},
    }
    _, bid_events, next_decision, _ = engine.apply_action(bid_action)

    assert any(event["type"] == "AUCTION_BID_PLACED" for event in bid_events)
    assert next_decision is not None
    drop_action = {
        "schema_version": "v1",
        "decision_id": next_decision["decision_id"],
        "action": "drop_out",
        "args": {},
    }
    cash_before = engine.state.players[1].cash
    _, drop_events, post_decision, _ = engine.apply_action(drop_action)

    assert engine.state.auction is None
    assert engine.state.board[target_index].owner_id == "p2"
    assert engine.state.players[1].cash == cash_before - 10
    ended = next(event for event in drop_events if event["type"] == "AUCTION_ENDED")
    assert ended["payload"]["reason"] == "SOLD"
    assert ended["payload"]["winner_player_id"] == "p2"
    assert ended["payload"]["winning_bid"] == 10
    assert post_decision is not None
    assert post_decision["decision_type"] == "POST_TURN_ACTION_DECISION"


def test_auction_end_no_bids() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]
    engine = Engine(seed=45, players=players, run_id="run-auction-nobids", max_turns=3, ts_step_ms=1)
    result = _start_auction(engine)
    target_index = result["target_index"]
    decision = result["decision"]

    action = {
        "schema_version": "v1",
        "decision_id": decision["decision_id"],
        "action": "drop_out",
        "args": {},
    }
    _, events, post_decision, _ = engine.apply_action(action)

    assert engine.state.auction is None
    assert engine.state.board[target_index].owner_id is None
    ended = next(event for event in events if event["type"] == "AUCTION_ENDED")
    assert ended["payload"]["reason"] == "NO_BIDS"
    assert ended["payload"]["winner_player_id"] is None
    assert ended["payload"]["winning_bid"] is None
    assert post_decision is not None
    assert post_decision["decision_type"] == "POST_TURN_ACTION_DECISION"


def test_auction_deterministic_replay() -> None:
    players = [
        {"player_id": "p1", "name": "P1"},
        {"player_id": "p2", "name": "P2"},
    ]

    def run_sequence(engine: Engine) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        engine.state.players[0].position = 10
        engine.state.active_player_id = "p1"
        engine._rng.roll_dice = lambda: (1, 3)
        engine.state.board[14].owner_id = None
        _, new_events, decision, _ = engine.advance_until_decision(max_steps=1)
        events.extend(new_events)
        assert decision is not None
        start_action = {
            "schema_version": "v1",
            "decision_id": decision["decision_id"],
            "action": "start_auction",
            "args": {},
        }
        _, new_events, decision, _ = engine.apply_action(start_action)
        events.extend(new_events)
        assert decision is not None
        bid_action = {
            "schema_version": "v1",
            "decision_id": decision["decision_id"],
            "action": "bid_auction",
            "args": {"bid_amount": 7},
        }
        _, new_events, decision, _ = engine.apply_action(bid_action)
        events.extend(new_events)
        assert decision is not None
        drop_action = {
            "schema_version": "v1",
            "decision_id": decision["decision_id"],
            "action": "drop_out",
            "args": {},
        }
        _, new_events, _, _ = engine.apply_action(drop_action)
        events.extend(new_events)
        return events

    engine_a = Engine(seed=50, players=players, run_id="run-auction-det", max_turns=3, ts_step_ms=1)
    engine_b = Engine(seed=50, players=players, run_id="run-auction-det", max_turns=3, ts_step_ms=1)

    events_a = run_sequence(engine_a)
    events_b = run_sequence(engine_b)

    assert events_a == events_b
