import React, { useEffect, useRef } from 'react';
import { SOCEvent } from '../hooks/useWebSocket';
import EventCard from './EventCard';

interface LiveFeedProps {
  events: SOCEvent[];
  onSelectEvent: (event: SOCEvent) => void;
}

export default function LiveFeed({ events, onSelectEvent }: LiveFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events]);

  const displayEvents = events.slice(-100); // Only keep last 100 in DOM

  return (
    <div className="bg-[#111826] border border-slate-800 rounded-xl shadow-sm flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-slate-800 pb-3">
        <h2 className="text-slate-400 font-semibold text-sm uppercase tracking-widest flex items-center gap-2">
          Event Stream
        </h2>
      </div>
      
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 scroll-smooth"
        style={{ scrollbarWidth: 'thin', scrollbarColor: '#334155 #0f172a' }}
      >
        {displayEvents.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 font-mono text-sm italic">
            Waiting for telemetry stream...
          </div>
        ) : (
          displayEvents.map((ev, i) => (
            <EventCard 
              key={`${ev.timestamp}-${i}`} 
              event={ev} 
              onClick={() => onSelectEvent(ev)} 
            />
          ))
        )}
      </div>
    </div>
  );
}
