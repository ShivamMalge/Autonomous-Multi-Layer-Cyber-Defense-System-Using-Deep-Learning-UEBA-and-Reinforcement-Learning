import React from 'react';
import { Play, Pause, RotateCcw, FastForward } from 'lucide-react';
import { StreamState } from '../hooks/useWebSocket';

interface ControlsProps {
  streamState: StreamState;
}

export default function Controls({ streamState }: ControlsProps) {
  const handlePlay = async () => await fetch("http://localhost:8000/api/play", { method: 'POST' });
  const handlePause = async () => await fetch("http://localhost:8000/api/pause", { method: 'POST' });
  const handleReset = async () => await fetch("http://localhost:8000/api/reset", { method: 'POST' });
  
  const handleSpeed = async (newSpeed: number) => {
    await fetch("http://localhost:8000/api/speed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speed: newSpeed })
    });
  };

  const progressPct = streamState.total_events > 0 
    ? (streamState.current_index / streamState.total_events) * 100 
    : 0;

  return (
    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex flex-col gap-3 shadow-lg">
      <div className="flex justify-between items-center">
        <h2 className="text-emerald-400 font-mono text-sm uppercase tracking-widest font-bold">Signal Control Array</h2>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className={streamState.playing ? "text-emerald-400" : "text-amber-500"}>
            {streamState.playing ? "▶ LIVE" : "⏸ PAUSED"}
          </span>
          <span className="text-slate-500 ml-2">
            EVENT {streamState.current_index} / {streamState.total_events}
          </span>
        </div>
      </div>
      
      <div className="flex items-center justify-between gap-4">
        <div className="flex bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
          <button onClick={handlePlay} className={`p-2 px-4 transition-colors ${streamState.playing ? 'bg-emerald-500/20 text-emerald-400' : 'hover:bg-slate-700 text-slate-300'}`}>
            <Play size={18} fill={streamState.playing ? "currentColor" : "none"} />
          </button>
          <button onClick={handlePause} className={`p-2 px-4 transition-colors ${!streamState.playing ? 'bg-amber-500/20 text-amber-400' : 'hover:bg-slate-700 text-slate-300'}`}>
            <Pause size={18} fill={!streamState.playing ? "currentColor" : "none"} />
          </button>
          <button onClick={handleReset} className="p-2 px-4 hover:bg-slate-700 transition-colors text-slate-300 group">
            <RotateCcw size={18} className="group-hover:-rotate-90 transition-transform duration-300" />
          </button>
        </div>

        <div className="flex-1 px-4">
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-300 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <div className="flex items-center gap-2 bg-slate-800 rounded-lg p-1 border border-slate-700">
          {[0.5, 1.0, 2.0, 5.0].map((s) => (
            <button
              key={s}
              onClick={() => handleSpeed(s)}
              className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                streamState.speed === s 
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
