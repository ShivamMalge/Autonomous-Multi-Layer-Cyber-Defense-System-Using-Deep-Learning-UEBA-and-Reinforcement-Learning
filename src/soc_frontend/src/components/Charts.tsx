import React from 'react';
import { SOCEvent } from '../hooks/useWebSocket';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  BarChart, Bar, Cell
} from 'recharts';

interface ChartsProps {
  events: SOCEvent[];
}

export default function Charts({ events }: ChartsProps) {
  // 1. Severity Area Chart Data
  const sevData = events.slice(-100).map((e, idx) => ({ time: idx, severity: e.severity_score }));

  // 2. Action Distribution
  const dist = events.reduce((acc, ev) => {
    acc[ev.final_action_name] = (acc[ev.final_action_name] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const barData = Object.keys(dist).map(k => ({ name: k, value: dist[k] }));

  const getColor = (name: string) => {
    if (name === "MONITOR") return "#22C55E";
    if (name === "ALERT") return "#F59E0B";
    if (name === "BLOCK_IP") return "#EF4444";
    if (name === "ISOLATE_USER") return "#a855f7";
    return "#374151";
  };

  return (
    <div className="flex flex-col gap-4 h-full min-h-0">
      
      {/* 1. SEVERITY TREND */}
      <div className="flex-1 flex flex-col min-h-0 bg-[#0B0F14] border border-slate-800 rounded-xl p-4 shadow-sm">
        <h3 className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider mb-2">Severity Over Time</h3>
        <div className="flex-1 min-h-[100px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sevData} margin={{ top: 5, right: 0, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="colorSev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <YAxis domain={[0, 1]} tick={{fontSize: 10, fill: '#6B7280'}} axisLine={false} tickLine={false}/>
              <Tooltip cursor={{stroke: '#374151'}} contentStyle={{ backgroundColor: '#111826', border: '1px solid #1F2937', borderRadius: '8px', color: '#E5E7EB', fontSize: '12px' }}/>
              <Area type="monotone" dataKey="severity" stroke="#EF4444" strokeWidth={2} fillOpacity={1} fill="url(#colorSev)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. ACTION DISTRIBUTION */}
      <div className="flex-1 flex flex-col min-h-0 bg-[#0B0F14] border border-slate-800 rounded-xl p-4 shadow-sm">
        <h3 className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider mb-2">Action Distribution</h3>
        <div className="flex-1 min-h-[100px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 10, left: -10, bottom: -10 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" tick={{fontSize: 10, fill: '#6B7280'}} axisLine={false} tickLine={false} width={80}/>
              <Tooltip cursor={{fill: '#1F2937'}} contentStyle={{ backgroundColor: '#111826', border: '1px solid #1F2937', borderRadius: '8px', color: '#E5E7EB', fontSize: '12px' }}/>
              <Bar dataKey="value" radius={[0,4,4,0]} isAnimationActive={false} barSize={12}>
                {barData.map((entry, index) => (<Cell key={`bcell-${index}`} fill={getColor(entry.name)} />))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}
