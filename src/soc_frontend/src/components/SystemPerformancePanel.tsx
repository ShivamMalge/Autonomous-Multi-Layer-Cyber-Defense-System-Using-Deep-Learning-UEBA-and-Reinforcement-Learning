import React, { useEffect, useState } from 'react';
import { Activity, Clock, Cpu, Server } from 'lucide-react';

export default function SystemPerformancePanel() {
  const [perf, setPerf] = useState<any>(null);

  useEffect(() => {
    const fetchPerf = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/perf');
        const data = await res.json();
        setPerf(data);
      } catch (e) {
        console.error("Perf fetch error", e);
      }
    };
    fetchPerf();
    const inv = setInterval(fetchPerf, 1000);
    return () => clearInterval(inv);
  }, []);

  if (!perf) return null;

  return (
    <div className="bg-[#111826] border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col justify-between h-full">
      <h2 className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider flex gap-2 items-center mb-3">
          System Performance
      </h2>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0B0F14] p-3 rounded-lg border border-slate-800 flex flex-col">
            <span className="text-slate-500 uppercase text-[10px] mb-1 font-medium flex items-center gap-1.5"><Clock size={12}/> Latency</span>
            <span className="text-slate-200 font-semibold text-lg">{perf.avg_latency_ms.toFixed(2)} <span className="text-xs text-slate-500 font-normal">ms</span></span>
        </div>
        <div className="bg-[#0B0F14] p-3 rounded-lg border border-slate-800 flex flex-col">
            <span className="text-slate-500 uppercase text-[10px] mb-1 font-medium flex items-center gap-1.5"><Activity size={12}/> Throughput</span>
            <span className="text-slate-200 font-semibold text-lg">{perf.throughput_eps.toLocaleString()} <span className="text-xs text-slate-500 font-normal">eps</span></span>
        </div>
        <div className="bg-[#0B0F14] p-3 rounded-lg border border-slate-800 flex flex-col">
            <span className="text-slate-500 uppercase text-[10px] mb-1 font-medium flex items-center gap-1.5"><Server size={12}/> Queue</span>
            <span className="text-slate-200 font-semibold text-lg">{perf.active_queue}</span>
        </div>
        <div className="bg-[#0B0F14] p-3 rounded-lg border border-slate-800 flex flex-col">
            <span className="text-slate-500 uppercase text-[10px] mb-1 font-medium flex items-center gap-1.5"><Cpu size={12}/> Uptime</span>
            <span className="text-slate-200 font-semibold text-lg">{perf.total_uptime_hrs}<span className="text-xs text-slate-500 font-normal">h</span></span>
        </div>
      </div>
    </div>
  );
}
