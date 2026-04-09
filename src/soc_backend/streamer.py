import asyncio
import logging
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from state import state

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_event(self, event_data: dict, current_index: int, total: int):
        payload = {
            "type": "NEW_EVENT",
            "event": event_data,
            "progress": {
                "current": current_index,
                "total": total
            }
        }
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(connection)

    async def broadcast_state(self):
        payload = {
            "type": "STATE_UPDATE",
            "state": {
                "playing": state.playing,
                "speed": state.speed,
                "current_index": state.current_index,
                "total_events": state.total_events
            }
        }
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

async def event_stream_loop(events: list):
    """Background task that streams events when playing."""
    base_delay = 0.5 # Default 500ms between events
    
    while True:
        if state.playing and state.current_index < state.total_events:
            # Emit current event
            event = events[state.current_index]
            state.current_index += 1
            
            await manager.broadcast_event(event, state.current_index, state.total_events)
            
            # Pause logic based on speed (higher speed = lower delay)
            delay = base_delay / max(state.speed, 0.1)
            await asyncio.sleep(delay)
            
        elif state.playing and state.current_index >= state.total_events:
            # Reached end
            state.playing = False
            await manager.broadcast_state()
            await asyncio.sleep(0.5)
        else:
            # Paused or idle
            await asyncio.sleep(0.1)
