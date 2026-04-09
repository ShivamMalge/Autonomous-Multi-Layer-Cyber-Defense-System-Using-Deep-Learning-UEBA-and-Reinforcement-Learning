import { useState, useEffect, useRef, useCallback } from 'react';

export interface SOCEvent {
  timestamp: string;
  ip: string;
  user_id: string;
  anomaly_score: number;
  user_risk_score: number;
  activity_intensity: number;
  severity_score: number;
  rl_action_name: string;
  final_action_name: string;
  was_downgraded: boolean;
  downgrade_reason: string;
  latency_ms: number;
}

export interface StreamState {
  playing: boolean;
  speed: number;
  current_index: number;
  total_events: number;
}

export function useWebSocket(url: string = "ws://localhost:8000/ws/stream") {
  const [events, setEvents] = useState<SOCEvent[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [streamState, setStreamState] = useState<StreamState>({
    playing: false,
    speed: 1.0,
    current_index: 0,
    total_events: 0
  });
  
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "STATE_UPDATE") {
          setStreamState(data.state);
          setIsPlaying(data.state.playing);
        } else if (data.type === "NEW_EVENT") {
          setEvents(prev => {
             // Keep rolling window of 100 max in memory
             const next = data.event.command === "WIPE" ? [] : [...prev, data.event];
             return next.slice(-100);
          });
          if (data.progress) {
            setStreamState(prev => ({
              ...prev,
              current_index: data.progress.current,
              total_events: data.progress.total
            }));
          }
        }
      } catch (err) {
        console.error("WebSocket parsing error:", err);
      }
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected");
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  const togglePlay = async () => {
    const newState = !isPlaying;
    setIsPlaying(newState);
    await fetch(`http://localhost:8000/api/${newState ? 'play' : 'pause'}`, { method: 'POST' });
  };

  const resetStream = async () => {
    setIsPlaying(false);
    await fetch("http://localhost:8000/api/reset", { method: 'POST' });
  };

  return { events, streamState, isPlaying, togglePlay, resetStream };
}
