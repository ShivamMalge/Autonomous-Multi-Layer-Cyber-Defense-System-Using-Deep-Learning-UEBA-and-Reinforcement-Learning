import React from 'react';
import { SOCEvent } from '../hooks/useWebSocket';
import { Radar, Users, Globe2, AlertTriangle } from 'lucide-react';

interface ThreatIntelligencePanelProps {
  events: SOCEvent[];
}

export default function ThreatIntelligencePanel({ events }: ThreatIntelligencePanelProps) {
  const windowEvents = events.slice(-100);

  // Cluster threats implicitly based on signatures. 
  // "Insider": High Risk, Low Anomaly
  // "External": High Anomaly, Low Risk
  // "Critical": Both High
  
  let insider = 0;
  let external = 0;
  let critical = 0;

  const dedupedUsers = new Set<string>();

  windowEvents.forEach(e => {
    if(dedupedUsers.has(e.user_id + e.ip)) return;
    dedupedUsers.add(e.user_id + e.ip);

    if (e.severity_score > 0.7) {
      if (e.user_risk_score > 0.6 && e.anomaly_score < 0.5) insider++;
      else if (e.anomaly_score > 0.7 && e.user_risk_score < 0.5) external++;
      else critical++;
    }
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg h-full flex flex-col relative overflow-hidden">
        {/* Radar sweeping background effect */}
        <div className="absolute -top-1/2 -right-1/2 w-full h-full border border-cyan-500/10 rounded-full animate-[spin_10s_linear_infinite] pointer-events-none opacity-20">
          <div className="w-1/2 h-full bg-gradient-to-r from-transparent to-cyan-500/20" />
        </div>

      <h3 className="text-cyan-400 font-mono text-xs uppercase tracking-wider mb-4 font-bold flex gap-2 items-center relative z-10">
        <Radar size={16} />
        Threat Archetyping
      </h3>

      <div className="flex-1 flex flex-col justify-around relative z-10 gap-2">
        
        {/* Insider Group */}
        <div className="bg-slate-800/40 border border-slate-700/50 p-2 rounded-lg flex items-center justify-between group hover:bg-slate-800 transition-colors">
            <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-500/20 rounded text-indigo-400 group-hover:bg-indigo-500/40">
                    <Users size={16} />
                </div>
                <div>
                   <div className="text-[10px] text-slate-400 font-mono uppercase">Insider Threat</div>
                   <div className="text-xs text-slate-500 line-clamp-1">Account Compromise / Lateral Config</div>
                </div>
            </div>
            <div className="text-lg font-bold font-mono text-indigo-400 pl-2">{insider}</div>
        </div>

        {/* External Group */}
        <div className="bg-slate-800/40 border border-slate-700/50 p-2 rounded-lg flex items-center justify-between group hover:bg-slate-800 transition-colors">
            <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-500/20 rounded text-amber-400 group-hover:bg-amber-500/40">
                    <Globe2 size={16} />
                </div>
                <div>
                   <div className="text-[10px] text-slate-400 font-mono uppercase">External Intrusion</div>
                   <div className="text-xs text-slate-500 line-clamp-1">Zero-Day Protocol / Exfiltration</div>
                </div>
            </div>
            <div className="text-lg font-bold font-mono text-amber-400 pl-2">{external}</div>
        </div>

        {/* Critical Group */}
        <div className="bg-slate-800/40 border border-slate-700/50 p-2 rounded-lg flex items-center justify-between group hover:bg-rose-500/10 transition-colors border-l-2 border-l-rose-500">
            <div className="flex items-center gap-3">
                <div className="p-2 bg-rose-500/20 rounded text-rose-400 group-hover:bg-rose-500/40 animate-pulse">
                    <AlertTriangle size={16} />
                </div>
                <div>
                   <div className="text-[10px] text-rose-400 font-mono uppercase font-bold">Multi-Vector Critical</div>
                   <div className="text-xs text-rose-500/70 line-clamp-1">Advanced Persistent Threat (APT)</div>
                </div>
            </div>
            <div className="text-lg font-bold font-mono text-rose-400 pl-2">{critical}</div>
        </div>

      </div>
    </div>
  );
}
