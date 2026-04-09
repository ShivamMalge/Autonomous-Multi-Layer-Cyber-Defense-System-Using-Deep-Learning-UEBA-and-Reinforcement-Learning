"use client";

import React, { useState } from "react";
import { useWebSocket, SOCEvent } from "../hooks/useWebSocket";
import LiveFeed from "../components/LiveFeed";
import FlowPipeline from "../components/FlowPipeline";
import Charts from "../components/Charts";
import SystemPerformancePanel from "../components/SystemPerformancePanel";
import { ShieldCheck, Play, Pause, RotateCcw } from "lucide-react";

export default function Home() {
  const { events, streamState, isPlaying, togglePlay, resetStream } = useWebSocket("ws://localhost:8000/ws/stream");
  const [selectedEvent, setSelectedEvent] = useState<SOCEvent | null>(null);

  const lastEvent = events.length > 0 ? events[events.length - 1] : null;
  const progressPct = streamState.total_events > 0 ? (streamState.current_index / streamState.total_events) * 100 : 0;

  return (
    <main className="min-h-screen p-4 font-sans transition-colors duration-300 ease-out">
      
      <div className="max-w-[1800px] mx-auto flex flex-col h-[calc(100vh-2rem)] gap-4 relative z-10">
        
        {/* HEADER & CONTROLS */}
        <header className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <ShieldCheck className="text-emerald-500" size={24} />
            <div>
              <h1 className="text-lg font-semibold text-slate-100 tracking-tight">SOC Defense Orchestrator</h1>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
             {/* Playback Controls natively handled */}
             <div className="flex bg-slate-800 rounded overflow-hidden border border-slate-700">
               <button onClick={togglePlay} className={`px-4 py-1.5 text-sm transition-colors flex items-center gap-2 ${isPlaying ? 'bg-emerald-600 text-white' : 'hover:bg-slate-700 text-slate-300'}`}>
                 {isPlaying ? <Pause size={14}/> : <Play size={14}/>} {isPlaying ? "PAUSE" : "LIVE"}
               </button>
               <button onClick={resetStream} className="px-3 hover:bg-slate-700 transition-colors text-slate-300">
                 <RotateCcw size={14} />
               </button>
             </div>
             
             <div className="w-32 h-1.5 bg-slate-800 rounded-full overflow-hidden">
               <div className="h-full bg-emerald-500 transition-all duration-300 ease-out" style={{ width: `${progressPct}%` }} />
             </div>
             <span className="text-xs text-slate-500 w-24 text-right">
                {streamState.current_index} / {streamState.total_events}
             </span>
          </div>
        </header>

        {/* 3 ZONE LAYOUT */}
        <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
          
          {/* ZONE 1: LIVE FEED (LEFT) */}
          <div className="col-span-3 h-full min-h-0">
            <LiveFeed events={events} onSelectEvent={setSelectedEvent} />
          </div>

          {/* ZONE 2: FLOW PIPELINE HERO (CENTER) */}
          <div className="col-span-6 h-full min-h-0">
            <FlowPipeline lastEvent={lastEvent} />
          </div>

          {/* ZONE 3: INSIGHTS (RIGHT) */}
          <div className="col-span-3 h-full min-h-0 flex flex-col gap-4">
             <div className="flex-1 bg-[#111826] rounded-xl border border-slate-800 p-4 shadow-sm min-h-0">
               <Charts events={events} />
             </div>
             <div className="h-48 shrink-0">
               <SystemPerformancePanel />
             </div>
          </div>

        </div>
      </div>

    </main>
  );
}
