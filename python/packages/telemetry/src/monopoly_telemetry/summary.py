from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .run_files import RunFiles


DEFAULT_STARTING_CASH = 1500


def build_summary(run_files: RunFiles) -> dict[str, Any]:
    events = _read_jsonl(run_files.events_path)
    decisions = _read_jsonl(run_files.decisions_path)
    actions = _read_jsonl(run_files.actions_path)
    board_spec = _load_board_spec()
    return _build_summary_from_logs(
        run_id=run_files.run_id,
        events=events,
        decisions=decisions,
        actions=actions,
        board_spec=board_spec,
    )


def _build_summary_from_logs(
    *,
    run_id: str,
    events: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    board_spec: dict[str, Any],
) -> dict[str, Any]:
    space_key_by_index, price_by_index = _build_space_maps(board_spec)
    player_name_by_id = _collect_player_names(decisions)
    player_ids = _collect_player_ids(events, decisions, actions, player_name_by_id)

    cash_by_player = {player_id: DEFAULT_STARTING_CASH for player_id in player_ids}
    bankrupt_by_player = {player_id: False for player_id in player_ids}
    owned_by_player: dict[str, set[int]] = {player_id: set() for player_id in player_ids}
    owner_by_index: dict[int, str | None] = {}
    mortgaged_by_index: dict[int, bool] = {}
    turns_played_by_player = {player_id: 0 for player_id in player_ids}
    turn_first_actor: dict[int, str] = {}

    pending_purchases: dict[str, list[dict[str, Any]]] = {player_id: [] for player_id in player_ids}
    acquisition_timeline: list[dict[str, Any]] = []

    winner_id = None
    stop_reason = None
    turn_count = 0

    for event in events:
        event_type = event.get("type")
        turn_index = int(event.get("turn_index", 0))
        if turn_index > turn_count:
            turn_count = turn_index

        if event_type == "LLM_DECISION_REQUESTED":
            payload = event.get("payload", {})
            player_id = payload.get("player_id")
            if isinstance(player_id, str) and turn_index not in turn_first_actor:
                turn_first_actor[turn_index] = player_id
                if player_id in turns_played_by_player:
                    turns_played_by_player[player_id] += 1
            continue

        if event_type == "CASH_CHANGED":
            payload = event.get("payload", {})
            player_id = payload.get("player_id")
            delta = payload.get("delta")
            reason = payload.get("reason")
            if isinstance(player_id, str) and isinstance(delta, int):
                cash_by_player.setdefault(player_id, DEFAULT_STARTING_CASH)
                cash_by_player[player_id] += delta
            if isinstance(player_id, str) and isinstance(reason, str):
                if reason.startswith("BANKRUPTCY"):
                    bankrupt_by_player[player_id] = True
                if reason == "BANKRUPTCY_ASSETS_TO_BANK":
                    for space_index, owner_id in list(owner_by_index.items()):
                        if owner_id == player_id:
                            owner_by_index[space_index] = None
                            mortgaged_by_index[space_index] = False
                            owned_by_player.get(player_id, set()).discard(space_index)
            if isinstance(player_id, str) and reason in {"buy_property", "auction_bid"}:
                queue = pending_purchases.get(player_id, [])
                if queue:
                    purchase = queue.pop(0)
                    space_index = purchase["space_index"]
                    method = "BUY" if reason == "buy_property" else "AUCTION"
                    acquisition_timeline.append(
                        {
                            "turn_index": purchase["turn_index"],
                            "player_id": player_id,
                            "space_key": space_key_by_index.get(space_index, f"SPACE_{space_index}"),
                            "method": method,
                        }
                    )
            continue

        if event_type == "PROPERTY_PURCHASED":
            payload = event.get("payload", {})
            player_id = payload.get("player_id")
            space_index = payload.get("space_index")
            price = payload.get("price")
            if isinstance(space_index, int):
                previous_owner = owner_by_index.get(space_index)
                if previous_owner:
                    owned_by_player.get(previous_owner, set()).discard(space_index)
                if isinstance(player_id, str):
                    owner_by_index[space_index] = player_id
                    owned_by_player.setdefault(player_id, set()).add(space_index)
                    if isinstance(price, int) and price > 0:
                        pending_purchases.setdefault(player_id, []).append(
                            {"space_index": space_index, "turn_index": turn_index}
                        )
            continue

        if event_type == "PROPERTY_TRANSFERRED":
            payload = event.get("payload", {})
            from_player_id = payload.get("from_player_id")
            to_player_id = payload.get("to_player_id")
            space_index = payload.get("space_index")
            if isinstance(space_index, int):
                if isinstance(from_player_id, str):
                    owned_by_player.get(from_player_id, set()).discard(space_index)
                if isinstance(to_player_id, str):
                    owner_by_index[space_index] = to_player_id
                    owned_by_player.setdefault(to_player_id, set()).add(space_index)
                    acquisition_timeline.append(
                        {
                            "turn_index": turn_index,
                            "player_id": to_player_id,
                            "space_key": space_key_by_index.get(space_index, f"SPACE_{space_index}"),
                            "method": "TRADE",
                        }
                    )
            continue

        if event_type == "PROPERTY_MORTGAGED":
            payload = event.get("payload", {})
            space_index = payload.get("space_index")
            if isinstance(space_index, int):
                mortgaged_by_index[space_index] = True
            continue

        if event_type == "PROPERTY_UNMORTGAGED":
            payload = event.get("payload", {})
            space_index = payload.get("space_index")
            if isinstance(space_index, int):
                mortgaged_by_index[space_index] = False
            continue

        if event_type == "GAME_ENDED":
            payload = event.get("payload", {})
            winner_id = payload.get("winner_player_id")
            stop_reason = payload.get("reason")

    decision_stats, token_usage = _build_decision_stats(decisions)

    players_summary: dict[str, Any] = {}
    for player_id in player_ids:
        cash = cash_by_player.get(player_id, DEFAULT_STARTING_CASH)
        owned = owned_by_player.get(player_id, set())
        property_value = 0
        mortgage_value = 0
        for space_index in owned:
            price = price_by_index.get(space_index) or 0
            property_value += price
            if mortgaged_by_index.get(space_index, False):
                mortgage_value += price // 2
        net_worth = cash + property_value - mortgage_value
        players_summary[player_id] = {
            "name": player_name_by_id.get(player_id),
            "cash": cash,
            "net_worth_estimate": net_worth,
            "bankrupt": bankrupt_by_player.get(player_id, False),
            "turns_played": turns_played_by_player.get(player_id, 0),
        }

    summary = {
        "run_id": run_id,
        "winner_player_id": winner_id,
        "turn_count": turn_count,
        "reason": stop_reason,
        "players": players_summary,
        "decision_stats": decision_stats,
        "property_acquisition_timeline": acquisition_timeline,
    }
    if token_usage is not None:
        summary["token_usage"] = token_usage
    return summary


def _build_decision_stats(decisions: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    resolved = [entry for entry in decisions if entry.get("phase") == "decision_resolved"]
    total = len(resolved)
    fallback_count = sum(1 for entry in resolved if entry.get("fallback_used"))
    invalid_attempts = 0
    latencies: list[int] = []
    token_usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    token_usage_seen = False
    cost_total = 0.0
    cost_seen = False

    for entry in resolved:
        for attempt in entry.get("attempts", []):
            errors = attempt.get("validation_errors") or []
            if errors:
                invalid_attempts += 1
            raw = attempt.get("raw_response") or {}
            usage = raw.get("usage") if isinstance(raw, dict) else None
            if isinstance(usage, dict):
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    value = usage.get(key)
                    if isinstance(value, int):
                        token_usage_totals[key] += value
                        token_usage_seen = True
                cost = usage.get("cost")
                if isinstance(cost, (int, float)):
                    cost_total += float(cost)
                    cost_seen = True
            if isinstance(raw, dict):
                cost = raw.get("cost") or raw.get("total_cost")
                if isinstance(cost, (int, float)):
                    cost_total += float(cost)
                    cost_seen = True

        latency = entry.get("latency_ms")
        if isinstance(latency, int):
            latencies.append(latency)

    avg_latency = int(sum(latencies) / len(latencies)) if latencies else None
    median_latency = _median(latencies) if latencies else None
    stats = {
        "total_decisions": total,
        "invalid_attempts": invalid_attempts,
        "fallbacks": fallback_count,
        "avg_latency_ms": avg_latency,
        "median_latency_ms": median_latency,
    }

    token_usage: dict[str, Any] | None = None
    if token_usage_seen or cost_seen:
        token_usage = {}
        if token_usage_seen:
            token_usage.update(token_usage_totals)
        if cost_seen:
            token_usage["total_cost"] = round(cost_total, 6)
    return stats, token_usage


def _median(values: list[int]) -> int:
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2:
        return sorted_vals[mid]
    return int((sorted_vals[mid - 1] + sorted_vals[mid]) / 2)


def _collect_player_names(decisions: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for entry in decisions:
        player_id = entry.get("player_id")
        player_name = entry.get("player_name")
        if isinstance(player_id, str) and isinstance(player_name, str):
            names[player_id] = player_name
    return names


def _collect_player_ids(
    events: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    player_name_by_id: dict[str, str],
) -> list[str]:
    ids: set[str] = set(player_name_by_id.keys())
    for entry in decisions:
        player_id = entry.get("player_id")
        if isinstance(player_id, str):
            ids.add(player_id)
    for entry in actions:
        player_id = entry.get("actor_player_id")
        if isinstance(player_id, str):
            ids.add(player_id)
    for event in events:
        actor = event.get("actor", {})
        player_id = actor.get("player_id") if isinstance(actor, dict) else None
        if isinstance(player_id, str):
            ids.add(player_id)
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            for key in (
                "player_id",
                "from_player_id",
                "to_player_id",
                "winner_player_id",
                "initiator_player_id",
                "counterparty_player_id",
                "bidder_player_id",
            ):
                value = payload.get(key)
                if isinstance(value, str):
                    ids.add(value)
    return sorted(ids)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries


def _resolve_repo_root() -> Path:
    start = Path(__file__).resolve()
    current = start if start.is_dir() else start.parent
    for parent in [current, *current.parents]:
        if (parent / "contracts").is_dir():
            return parent
    raise RuntimeError("Repo root not found (expected contracts/).")


def _normalize_space_key(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    return cleaned.strip("_").upper()


def _load_board_spec() -> dict[str, Any]:
    repo_root = _resolve_repo_root()
    board_path = repo_root / "contracts" / "data" / "board.json"
    return json.loads(board_path.read_text(encoding="utf-8"))


def _build_space_maps(board_spec: dict[str, Any]) -> tuple[dict[int, str], dict[int, int]]:
    space_key_by_index: dict[int, str] = {}
    price_by_index: dict[int, int] = {}
    for space in board_spec.get("spaces", []):
        if not isinstance(space, dict):
            continue
        index = int(space.get("index", 0))
        name = str(space.get("name", ""))
        price = space.get("price")
        space_key_by_index[index] = _normalize_space_key(name)
        price_by_index[index] = int(price) if price is not None else 0
    return space_key_by_index, price_by_index
