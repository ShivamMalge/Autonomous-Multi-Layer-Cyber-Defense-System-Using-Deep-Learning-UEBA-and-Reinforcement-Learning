from pydantic import BaseModel

class PlaybackState(BaseModel):
    playing: bool = False
    speed: float = 1.0
    current_index: int = 0
    total_events: int = 0

class AppState:
    """Global state of the SOC streaming backend."""
    def __init__(self):
        self.playing = False
        self.speed = 1.0  # 1.0x is normal. Higher means faster stream (less delay)
        self.current_index = 0
        self.total_events = 0
        
    def reset(self):
        self.current_index = 0
        self.playing = False

state = AppState()
