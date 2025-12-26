from __future__ import annotations

import time
from fastapi import FastAPI, WebSocket
from fastapi import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from monopoly_api.run_manager import RunManager
from monopoly_api.settings import load_settings

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
    name: str


class StartRunRequest(BaseModel):
    seed: int | None = None
    players: list[PlayerSpec] | None = None


@app.post("/run/start")
async def run_start(body: StartRunRequest) -> dict:
    seed = body.seed if body.seed is not None else int(time.time())
    if body.players:
        players = [player.model_dump() for player in body.players]
    else:
        players = [
            {"player_id": "p1", "name": "Player 1"},
            {"player_id": "p2", "name": "Player 2"},
            {"player_id": "p3", "name": "Player 3"},
            {"player_id": "p4", "name": "Player 4"},
        ]
    run_id = await run_manager.start_run(seed=seed, players=players)
    return {"run_id": run_id}


@app.post("/run/stop")
async def run_stop() -> dict:
    await run_manager.stop_run()
    return {"ok": True}


@app.get("/run/status")
def run_status() -> dict:
    return run_manager.get_status()


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
