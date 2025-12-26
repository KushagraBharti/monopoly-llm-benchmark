from __future__ import annotations

import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Monopoly LLM Benchmark API")

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


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "hello", "msg": "connected"})
    try:
        while True:
            # Echo incoming messages for now
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": data})
    except Exception:
        # Client disconnected
        return
