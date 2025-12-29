from __future__ import annotations

import time
from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from monopoly_api.run_manager import RunManager
from monopoly_api.settings import load_settings
from monopoly_arena import build_player_configs
from monopoly_arena.player_config import EXPECTED_PLAYER_COUNT

app = FastAPI(title="Monopoly LLM Benchmark API")
settings = load_settings()
run_manager = RunManager(settings.runs_dir)

# Allow local dev frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


class PlayerSpec(BaseModel):
    player_id: str
    name: str | None = None
    openrouter_model_id: str | None = None
    system_prompt: str | None = None


class StartRunRequest(BaseModel):
    seed: int | None = None
    players: list[PlayerSpec] | None = None


@app.post("/run/start")
async def run_start(body: StartRunRequest) -> dict:
    seed = body.seed if body.seed is not None else int(time.time())
    requested_players = [player.model_dump(exclude_none=True) for player in body.players] if body.players else None
    try:
        players = build_player_configs(
            requested_players=requested_players,
            config_path=settings.players_config_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if len(players) != EXPECTED_PLAYER_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Exactly {EXPECTED_PLAYER_COUNT} players are required for LLM runs.",
        )
    run_id = await run_manager.start_run(seed=seed, players=players)
    return {"run_id": run_id}


@app.post("/run/stop")
async def run_stop() -> dict:
    await run_manager.stop_run()
    return {"ok": True}


@app.post("/run/pause")
async def run_pause() -> dict:
    await run_manager.pause()
    return {"ok": True}


@app.post("/run/resume")
async def run_resume() -> dict:
    await run_manager.resume()
    return {"ok": True}


@app.get("/run/status")
def run_status() -> dict:
    return run_manager.get_status()


@app.get("/run/decisions/recent")
def run_decisions_recent(limit: int = Query(50, ge=1, le=200)) -> dict:
    return {"decisions": run_manager.get_recent_decisions(limit)}


@app.get("/run/decision/{decision_id}")
def run_decision(decision_id: str) -> dict:
    bundle = run_manager.get_decision_bundle(decision_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return bundle


@app.get("/runs/{run_id}/decisions")
def runs_decisions(run_id: str, limit: int | None = Query(None, ge=1, le=1000)) -> dict:
    decisions = run_manager.get_decisions_for_run(run_id, limit=limit)
    if decisions is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "decisions": decisions}


@app.get("/runs/{run_id}/decisions/{decision_id}")
def runs_decision_detail(run_id: str, decision_id: str) -> dict:
    bundle = run_manager.get_decision_bundle_for_run(run_id, decision_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return bundle


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        await run_manager.subscribe(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.send_json(
            {
                "type": "ERROR",
                "payload": {
                    "schema_version": "v1",
                    "message": "WebSocket error",
                    "details": None,
                },
            }
        )
    finally:
        await run_manager.unsubscribe(websocket)
