from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from monopoly_telemetry import init_run_files

from .llm_runner import LlmRunner
from .openrouter_client import OpenRouterClient
from .paths import default_players_config_path, resolve_repo_root, resolve_repo_path
from .player_config import PlayerConfig, build_player_configs


def _generate_run_id(seed: int, players: list[PlayerConfig]) -> str:
    players_blob = [
        {
            "player_id": player.player_id,
            "name": player.name,
            "openrouter_model_id": player.openrouter_model_id,
            "system_prompt": player.system_prompt,
        }
        for player in players
    ]
    seed_blob = json.dumps({"seed": seed, "players": players_blob}, sort_keys=True)
    digest = hashlib.sha1(seed_blob.encode("utf-8")).hexdigest()[:8]
    return f"headless-{seed}-{digest}"


async def _run(args: argparse.Namespace) -> int:
    runs_dir = resolve_repo_path(args.runs_dir) if args.runs_dir else resolve_repo_root() / "runs"
    players_path = resolve_repo_path(args.players) if args.players else default_players_config_path()
    players = build_player_configs(requested_players=None, config_path=players_path)
    run_id = args.run_id or _generate_run_id(args.seed, players)
    run_files = init_run_files(runs_dir, run_id)

    runner = LlmRunner(
        seed=args.seed,
        players=players,
        run_id=run_id,
        openrouter=OpenRouterClient(),
        run_files=run_files,
        max_turns=args.max_turns,
        event_delay_s=args.event_delay_s,
        start_ts_ms=0,
        ts_step_ms=args.ts_step_ms,
    )

    stop_after_decisions = args.stop_after_decisions
    resolved_count = 0

    async def on_event(event: dict[str, Any]) -> None:
        run_files.write_event(event)

    async def on_snapshot(snapshot: dict[str, Any]) -> None:
        run_files.write_snapshot(snapshot)

    async def on_summary(summary: dict[str, Any]) -> None:
        run_files.write_summary(summary)

    async def on_decision(entry: dict[str, Any]) -> None:
        nonlocal resolved_count
        run_files.write_decision(entry)
        if entry.get("phase") == "decision_resolved":
            resolved_count += 1
            if stop_after_decisions is not None and resolved_count >= stop_after_decisions:
                runner.request_stop("STOP_AFTER_DECISIONS")

    await runner.run(on_event=on_event, on_snapshot=on_snapshot, on_summary=on_summary, on_decision=on_decision)
    print(str(run_files.run_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m monopoly_arena.run")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--players", type=str, default=None, help="Path to players.json (defaults to API config).")
    parser.add_argument("--runs-dir", type=str, default=None, help="Runs output dir (defaults to repo_root/runs).")
    parser.add_argument("--run-id", type=str, default=None, help="Override run id (default is deterministic).")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--event-delay-s", type=float, default=0.0)
    parser.add_argument("--ts-step-ms", type=int, default=250)
    parser.add_argument("--stop-after-decisions", type=int, default=None)
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())

