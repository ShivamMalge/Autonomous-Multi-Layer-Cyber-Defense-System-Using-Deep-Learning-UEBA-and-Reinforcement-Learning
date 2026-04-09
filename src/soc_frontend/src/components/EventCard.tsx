import React from 'react';
import { SOCEvent } from '../hooks/useWebSocket';

interface EventCardProps {
  event: SOCEvent;
  onClick: () => void;
}

export default function EventCard({ event, onClick }: EventCardProps) {
  const getActionColor = (action: string) => {
    switch (action) {
      case 'MONITOR': return 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400';
      case 'ALERT': return 'bg-amber-500/20 border-amber-500/50 text-amber-400';
      case 'BLOCK_IP': return 'bg-rose-500/20 border-rose-500/50 text-rose-400';
      case 'ISOLATE_USER': return 'bg-purple-500/20 border-purple-500/50 text-purple-400';
      default: return 'bg-slate-800 border-slate-700 text-slate-300';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'MONITOR': return '🟢';
      case 'ALERT': return '⚠️';
      case 'BLOCK_IP': return '🔴';
      case 'ISOLATE_USER': return '☣️';
      default: return '⚪';
    }
  };

  const colorClass = getActionColor(event.final_action_name);
  const isIntervention = event.was_downgraded;

  return (
    <div 
      onClick={onClick}
      className="bg-[#0B0F14] border border-slate-800 rounded-lg p-4 mb-3 cursor-pointer transition-colors hover:border-slate-600 shadow-sm"
    >
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center gap-2 text-slate-300">
          <span>{getActionIcon(event.final_action_name)}</span>
          <span className="text-sm font-medium">{event.timestamp.substring(11, 19)}</span>
        </div>
      </div>

      <div className="text-slate-400 text-xs mb-3 flex flex-col gap-1">
        <div>User: <span className="text-slate-200">{event.user_id}</span></div>
        <div>IP: <span className="text-slate-200">{event.ip}</span></div>
      </div>

      <div className="flex items-center gap-2 mt-2 mb-2">
        <span className="text-xs text-slate-500">Severity</span>
        <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500"
            style={{ width: `${Math.min(event.severity_score * 100, 100)}%` }}
          />
        </div>
      </div>

      {isIntervention ? (
        <div className="mt-2 text-xs pt-2">
          <span className="text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">Override</span>
        </div>
      ) : null}
    </div>
  );
}
