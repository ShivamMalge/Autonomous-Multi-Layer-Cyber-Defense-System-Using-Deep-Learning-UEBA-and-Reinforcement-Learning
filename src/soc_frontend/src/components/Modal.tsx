import React from 'react';
import { SOCEvent } from '../hooks/useWebSocket';
import { ArrowRight, FileJson, Info } from 'lucide-react';

interface ModalProps {
  event: SOCEvent | null;
  onClose: () => void;
}

export default function Modal({ event, onClose }: ModalProps) {
  if (!event) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-[#0A0E17] border border-cyan-900 w-full max-w-4xl rounded-2xl shadow-[0_0_50px_rgba(34,211,238,0.1)] overflow-hidden flex flex-col max-h-[90vh]">
        
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900">
          <h2 className="text-xl font-bold font-mono text-cyan-400 flex items-center gap-2">
            <Info size={20} />
            Forensic Intelligence Drill-Down
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white px-3 py-1 rounded bg-slate-800 hover:bg-rose-500/20 font-mono text-sm border border-slate-700">ESC</button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 font-mono text-sm grid grid-cols-2 gap-6">
          
          {/* EVENT STORY VIEW */}
          <div className="col-span-2 bg-slate-900/50 p-5 rounded-xl border border-slate-800 shadow-inner">
            <h3 className="text-amber-400 font-bold mb-4 uppercase tracking-wide flex items-center gap-2">
              Pipeline Execution Story
            </h3>
            
            <div className="flex items-stretch justify-between relative">
               <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-800 -z-10 -translate-y-1/2"></div>
               
               {/* Step 1: Detection */}
               <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg text-center flex-1 mx-2 relative z-10 shadow-lg">
                  <div className="text-[10px] text-slate-500 uppercase mb-1">Step 1: Detection</div>
                  <div className="text-emerald-400 font-bold">Anomaly: {event.anomaly_score.toFixed(2)}</div>
                  <div className="text-amber-400 font-bold">Risk: {event.user_risk_score.toFixed(2)}</div>
               </div>

               <div className="flex items-center text-slate-600"><ArrowRight /></div>

               {/* Step 2: Inference */}
               <div className="bg-slate-900 border border-purple-900 p-3 rounded-lg text-center flex-1 mx-2 relative z-10 shadow-lg shadow-purple-900/20">
                  <div className="text-[10px] text-slate-500 uppercase mb-1">Step 2: RL Inference</div>
                  <div className="text-purple-400 font-bold">Action Suggested:</div>
                  <div className="text-white bg-purple-500/20 rounded px-2 py-0.5 mt-1">{event.rl_action_name}</div>
               </div>

               <div className="flex items-center text-slate-600"><ArrowRight /></div>

               {/* Step 3: Orchestrator */}
               <div className={`bg-slate-900 border p-3 rounded-lg text-center flex-1 mx-2 relative z-10 shadow-lg ${event.was_downgraded ? 'border-amber-700 shadow-amber-900/20' : 'border-emerald-900 shadow-emerald-900/20'}`}>
                  <div className="text-[10px] text-slate-500 uppercase mb-1">Step 3: Security Constraints</div>
                  <div className={event.was_downgraded ? "text-amber-400 font-bold" : "text-emerald-400 font-bold"}>
                      {event.was_downgraded ? "OVERRIDDEN" : "APPROVED"}
                  </div>
                  {event.was_downgraded && <div className="text-[9px] text-amber-500/70 mt-1 leading-tight">{event.downgrade_reason}</div>}
               </div>

               <div className="flex items-center text-slate-600"><ArrowRight /></div>

               {/* Step 4: Final Reaction */}
               <div className="bg-slate-900 border border-rose-900 p-3 rounded-lg text-center flex-1 mx-2 relative z-10 shadow-lg shadow-rose-900/20">
                  <div className="text-[10px] text-slate-500 uppercase mb-1">Step 4: Final Executed</div>
                  <div className="text-rose-400 font-bold text-lg pb-1">{event.final_action_name}</div>
               </div>
            </div>
          </div>

          {/* TELEMETRY */}
          <div className="col-span-2">
             <h3 className="text-blue-400 font-bold mb-2 uppercase tracking-wide flex items-center gap-2">
                <FileJson size={16} /> Raw Telemetry JSON
             </h3>
             <pre className="bg-[#05080f] p-4 rounded-xl text-slate-400 overflow-x-auto border border-slate-800 shadow-inner text-[11px] leading-relaxed">
               <code>{JSON.stringify(event, null, 2)}</code>
             </pre>
          </div>
          
        </div>
      </div>
    </div>
  );
}
