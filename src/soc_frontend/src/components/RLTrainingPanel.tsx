import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ComposedChart } from 'recharts';
import { Brain, Activity } from 'lucide-react';

export default function RLTrainingPanel() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/rl_metrics')
      .then(res => res.json())
      .then(d => setData(d))
      .catch(e => console.error(e));
  }, []);

  if (data.length === 0) return null;

  const latest = data[data.length - 1];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg shadow-black/50 flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-800 cursor-default">
        <h2 className="text-[#a855f7] font-mono text-sm uppercase tracking-widest font-bold flex gap-2 items-center">
            <Brain size={18} /> Deep Q-Network Optimization History
        </h2>
        <div className="text-xs font-mono flex gap-4">
            <div className="flex flex-col"><span className="text-slate-500 uppercase">Episodes</span><span className="text-slate-300 font-bold">{latest.episode}</span></div>
            <div className="flex flex-col"><span className="text-slate-500 uppercase">Total Steps</span><span className="text-slate-300 font-bold">{latest.total_steps.toLocaleString()}</span></div>
            <div className="flex flex-col"><span className="text-slate-500 uppercase">Final Loss</span><span className="text-emerald-400 font-bold">{latest.loss.toFixed(4)}</span></div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-4 text-xs font-mono">
        
        {/* REWARD CURVE */}
        <div className="flex flex-col relative">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-emerald-500/5 to-transparent pointer-events-none"></div>
          <h3 className="text-emerald-400 mb-2 opacity-80 uppercase z-10 font-bold">Reward Convergence Surface</h3>
          <div className="flex-1 min-h-0 z-10 relative left-[-15px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <XAxis dataKey="episode" hide />
                <YAxis domain={[0, 100]} tick={{fontSize: 9, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="reward" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive={true} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* LOSS & EPSILON CURVE */}
        <div className="flex flex-col relative">
          <h3 className="text-rose-400 mb-2 opacity-80 uppercase font-bold flex justify-between">
              <span>Optimization Loss Trajectory</span>
               <span className="text-amber-400/80 text-[9px] flex items-center gap-1"><Activity size={10}/> Epsilon Decay</span>
          </h3>
          <div className="flex-1 min-h-0 relative left-[-15px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data}>
                <XAxis dataKey="episode" hide />
                <YAxis yAxisId="left" domain={[0, 'auto']} tick={{fontSize: 9, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" domain={[0, 1]} tick={{fontSize: 9, fill: '#f59e0b'}} axisLine={false} tickLine={false}/>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px' }} />
                <Line yAxisId="left" type="monotone" dataKey="loss" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={true} />
                <Line yAxisId="right" type="monotone" dataKey="epsilon" stroke="#f59e0b" strokeWidth={1} strokeDasharray="3 3" dot={false} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
