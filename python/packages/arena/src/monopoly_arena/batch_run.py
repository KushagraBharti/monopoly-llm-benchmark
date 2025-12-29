from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from monopoly_telemetry import build_summary, init_run_files

from .llm_runner import LlmRunner
from .openrouter_client import OpenRouterClient
from .paths import default_players_config_path, resolve_repo_path, resolve_repo_root
from .player_config import PlayerConfig, build_player_configs


def _generate_run_id(batch_id: str, index: int, seed: int, players: list[PlayerConfig]) -> str:
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
    return f"{batch_id}-{index:03d}-{seed}-{digest}"


async def run_batch(
    config: dict[str, Any],
    *,
    runs_dir: Path | None = None,
    openrouter_factory: Callable[[], Any] | None = None,
) -> Path:
    batch_id = str(config.get("batch_id") or config.get("output_dir") or "batch")
    seeds = [int(seed) for seed in config.get("seeds", []) if isinstance(seed, (int, float))]
    matches = int(config.get("matches", len(seeds) if seeds else 0))
    players_path = config.get("players")
    players_file = (
        resolve_repo_path(str(players_path))
        if players_path
        else default_players_config_path()
    )

    if matches <= 0:
        raise ValueError("Batch matches must be >= 1.")
    if not seeds:
        raise ValueError("Batch config must include a non-empty seeds list.")

    runs_root = resolve_repo_path(str(runs_dir)) if runs_dir else resolve_repo_root() / "runs"
    batch_dir = runs_root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    index_path = batch_dir / "index.jsonl"

    players = build_player_configs(requested_players=None, config_path=players_file)
    factory = openrouter_factory or OpenRouterClient

    for match_index in range(matches):
        seed = seeds[match_index % len(seeds)]
        run_id = _generate_run_id(batch_id, match_index, seed, players)
        run_files = init_run_files(runs_root, run_id)
        runner = LlmRunner(
            seed=seed,
            players=players,
            run_id=run_id,
            openrouter=factory(),
            run_files=run_files,
            event_delay_s=0,
        )

        run_files.write_snapshot(runner.get_snapshot())

        async def on_event(event: dict[str, Any]) -> None:
            run_files.write_event(event)

        async def on_snapshot(snapshot: dict[str, Any]) -> None:
            run_files.write_snapshot(snapshot)

        async def on_summary(summary: dict[str, Any]) -> None:
            run_files.write_summary(summary)

        async def on_decision(entry: dict[str, Any]) -> None:
            run_files.write_decision(entry)

        await runner.run(
            on_event=on_event,
            on_snapshot=on_snapshot,
            on_summary=on_summary,
            on_decision=on_decision,
        )

        summary = build_summary(run_files)
        index_entry = {
            "run_id": run_id,
            "seed": seed,
            "run_dir": str(run_files.run_dir),
            "summary": {
                "winner_player_id": summary.get("winner_player_id"),
                "turn_count": summary.get("turn_count"),
                "reason": summary.get("reason"),
            },
        }
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(index_entry, separators=(",", ":"), ensure_ascii=True))
            handle.write("\n")

    return index_path


def _load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m monopoly_arena.batch_run")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--runs-dir", type=str, default=None)
    args = parser.parse_args(argv)

    config_path = resolve_repo_path(args.config)
    runs_dir = resolve_repo_path(args.runs_dir) if args.runs_dir else None
    config = _load_config(config_path)
    asyncio.run(run_batch(config, runs_dir=runs_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
