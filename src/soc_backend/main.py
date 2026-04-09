import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from state import state
from streamer import manager, event_stream_loop
from event_loader import load_events
from rl_logs import generate_rl_training_curves, generate_performance_metrics

app = FastAPI(title="Autonomous SOC Backend API")

# Setup CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In prod, restrict to localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
LOG_FILE = os.path.join(PROJECT_ROOT, "reports", "logs", "system_events.jsonl")

events = []

@app.on_event("startup")
async def startup_event():
    global events
    events = load_events(LOG_FILE)
    state.total_events = len(events)
    # Start the background streaming task
    asyncio.create_task(event_stream_loop(events))

class SpeedRequest(BaseModel):
    speed: float

@app.get("/api/state")
async def get_state():
    return {
        "playing": state.playing,
        "speed": state.speed,
        "current_index": state.current_index,
        "total_events": state.total_events
    }

@app.post("/api/play")
async def play():
    if state.current_index >= state.total_events:
        state.current_index = 0
    state.playing = True
    await manager.broadcast_state()
    return {"status": "playing"}

@app.post("/api/pause")
async def pause():
    state.playing = False
    await manager.broadcast_state()
    return {"status": "paused"}

@app.post("/api/reset")
async def reset():
    state.reset()
    await manager.broadcast_state()
    
    # Push a wipe command to frontend to clear UI state
    await manager.broadcast_event({"command": "WIPE"}, 0, state.total_events)
    return {"status": "reset"}

@app.post("/api/speed")
async def set_speed(req: SpeedRequest):
    state.speed = req.speed
    await manager.broadcast_state()
    return {"status": "speed_updated", "speed": state.speed}

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send current state upon connection
    await manager.broadcast_state()
    try:
        while True:
            # Just keep connection alive, actual streaming runs in background task
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/rl_metrics")
async def get_rl_metrics():
    return generate_rl_training_curves()

@app.get("/api/perf")
async def get_perf():
    return generate_performance_metrics()
