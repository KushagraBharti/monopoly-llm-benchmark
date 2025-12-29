from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from fastapi import WebSocket

from monopoly_telemetry import RunFiles, init_run_files

from monopoly_api.mock_runner import build_idle_snapshot
from monopoly_arena import LlmRunner, OpenRouterClient, PlayerConfig
from monopoly_arena.player_config import EXPECTED_PLAYER_COUNT
from monopoly_api.ws_protocol import make_event, make_hello, make_snapshot
from monopoly_api.decision_index import DecisionIndex


class RunManager:
    def __init__(
        self,
        runs_dir: Path,
        *,
        runner_factory: Callable[..., LlmRunner] | None = None,
        openrouter_factory: Callable[[], OpenRouterClient] | None = None,
    ) -> None:
        self._runs_dir = runs_dir
        self._clients: set[WebSocket] = set()
        self._runner: LlmRunner | None = None
        self._runner_task: asyncio.Task[None] | None = None
        self._run_id: str | None = None
        self._snapshot: dict[str, Any] | None = None
        self._seq: int | None = None
        self._turn_index: int | None = None
        self._telemetry: RunFiles | None = None
        self._players: list[PlayerConfig] = []
        self._decision_index: DecisionIndex | None = None
        self._paused = False
        self._lock = asyncio.Lock()
        self._runner_factory = runner_factory or LlmRunner
        self._openrouter_factory = openrouter_factory or OpenRouterClient

    async def start_run(self, seed: int, players: list[PlayerConfig]) -> str:
        async with self._lock:
            if len(players) != EXPECTED_PLAYER_COUNT:
                raise ValueError(f"Exactly {EXPECTED_PLAYER_COUNT} players are required for LLM runs.")
            run_id = self._generate_run_id(seed, players)
            if self._is_running() and self._run_id == run_id:
                return run_id
            if self._runner_task is not None and self._runner_task.done():
                self._runner_task = None
            if self._is_running():
                await self._stop_run_locked()
            self._run_id = run_id
            self._telemetry = init_run_files(self._runs_dir, run_id)
            self._decision_index = DecisionIndex(self._telemetry)
            self._players = players
            self._runner = self._runner_factory(
                seed=seed,
                players=players,
                run_id=run_id,
                openrouter=self._openrouter_factory(),
                run_files=self._telemetry,
            )
            self._paused = False
            self._snapshot = self._runner.get_snapshot()
            self._turn_index = self._snapshot["turn_index"]
            self._seq = None
            await self.broadcast_snapshot(self._snapshot)
            self._runner_task = asyncio.create_task(self._run_loop(run_id))
            return run_id

    async def stop_run(self) -> None:
        async with self._lock:
            await self._stop_run_locked()

    def get_status(self) -> dict[str, Any]:
        running = self._is_running()
        return {
            "running": running,
            "paused": self._paused,
            "run_id": self._run_id,
            "turn_index": self._turn_index,
            "connected_clients": len(self._clients),
            "players": [player.to_status() for player in self._players],
        }

    def get_snapshot(self) -> dict[str, Any]:
        if self._snapshot is None:
            return build_idle_snapshot()
        return copy.deepcopy(self._snapshot)

    async def subscribe(self, websocket: WebSocket) -> None:
        self._clients.add(websocket)
        try:
            await websocket.send_json(make_hello(self._run_id))
            await websocket.send_json(make_snapshot(self.get_snapshot()))
        except Exception:
            self._clients.discard(websocket)

    async def unsubscribe(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def broadcast_event(self, event: dict[str, Any]) -> None:
        self._seq = event.get("seq")
        self._turn_index = event.get("turn_index")
        if self._telemetry is not None:
            self._telemetry.write_event(event)
        await self._broadcast(make_event(event))

    async def broadcast_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot
        self._turn_index = snapshot.get("turn_index")
        if self._telemetry is not None:
            self._telemetry.write_snapshot(snapshot)
        await self._broadcast(make_snapshot(snapshot))

    async def _run_loop(self, run_id: str) -> None:
        runner = self._runner
        if runner is None or self._run_id != run_id:
            return
        await runner.run(
            on_event=self.broadcast_event,
            on_snapshot=self.broadcast_snapshot,
            on_summary=self._write_summary,
            on_decision=self._record_decision,
        )

    async def _write_summary(self, summary: dict[str, Any]) -> None:
        if self._telemetry is not None:
            self._telemetry.write_summary(summary)

    async def _broadcast(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        clients = list(self._clients)
        results = await asyncio.gather(
            *(self._safe_send(client, message) for client in clients),
            return_exceptions=True,
        )
        for client, result in zip(clients, results):
            if isinstance(result, Exception):
                self._clients.discard(client)

    async def _safe_send(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        await websocket.send_json(message)

    async def _stop_run_locked(self) -> None:
        if self._runner_task is None:
            return
        if self._runner is not None:
            self._runner.request_stop("STOPPED")
            self._runner.resume()
        task = self._runner_task
        if task is not None and not task.done():
            task.cancel()
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._runner_task = None
        self._runner = None
        self._paused = False

    @staticmethod
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
        return f"mock-{seed}-{digest}"

    async def _record_decision(self, entry: dict[str, Any]) -> None:
        if self._telemetry is not None:
            self._telemetry.write_decision(entry)
        if self._decision_index is not None:
            self._decision_index.record_entry(entry)

    async def pause(self) -> None:
        async with self._lock:
            if self._runner is None or not self._is_running() or self._paused:
                return
            self._paused = True
            self._runner.pause()

    async def resume(self) -> None:
        async with self._lock:
            if self._runner is None or not self._is_running():
                self._paused = False
                return
            if not self._paused:
                return
            self._paused = False
            self._runner.resume()

    def get_recent_decisions(self, limit: int) -> list[dict[str, Any]]:
        if self._decision_index is None:
            return []
        return self._decision_index.recent(limit=limit)

    def get_decision_bundle(self, decision_id: str) -> dict[str, Any] | None:
        if self._decision_index is None:
            return None
        return self._decision_index.get_bundle(decision_id)

    def _is_running(self) -> bool:
        return self._runner_task is not None and not self._runner_task.done()
