from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import WebSocket

from monopoly_telemetry import RunFiles, init_run_files

from monopoly_api.mock_runner import build_idle_snapshot
from monopoly_arena import LlmRunner, OpenRouterClient, PlayerConfig
from monopoly_api.ws_protocol import make_event, make_hello, make_snapshot


class RunManager:
    def __init__(self, runs_dir: Path) -> None:
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
        self._lock = asyncio.Lock()

    async def start_run(self, seed: int, players: list[PlayerConfig]) -> str:
        async with self._lock:
            if self._runner_task is not None:
                await self._stop_run_locked()
            if len(players) != 4:
                raise ValueError("Exactly 4 players are required for LLM runs.")
            run_id = self._generate_run_id(seed, players)
            self._run_id = run_id
            self._telemetry = init_run_files(self._runs_dir, run_id)
            self._players = players
            self._runner = LlmRunner(
                seed=seed,
                players=players,
                run_id=run_id,
                openrouter=OpenRouterClient(),
                run_files=self._telemetry,
            )
            self._snapshot = self._runner.get_snapshot()
            self._turn_index = self._snapshot["turn_index"]
            self._seq = None
            await self.broadcast_snapshot(self._snapshot)
            self._runner_task = asyncio.create_task(self._run_loop())
            return run_id

    async def stop_run(self) -> None:
        async with self._lock:
            await self._stop_run_locked()

    def get_status(self) -> dict[str, Any]:
        running = self._runner_task is not None and not self._runner_task.done()
        return {
            "running": running,
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

    async def _run_loop(self) -> None:
        if self._runner is None:
            return
        await self._runner.run(
            on_event=self.broadcast_event,
            on_snapshot=self.broadcast_snapshot,
            on_summary=self._write_summary,
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
        await self._runner_task
        self._runner_task = None

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
