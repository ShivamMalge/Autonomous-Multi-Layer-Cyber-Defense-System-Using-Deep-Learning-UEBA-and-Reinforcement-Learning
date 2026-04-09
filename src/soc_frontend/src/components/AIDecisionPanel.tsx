import React from 'react';
import { SOCEvent } from '../hooks/useWebSocket';
import { BrainCircuit } from 'lucide-react';

interface AIDecisionPanelProps {
  lastEvent: SOCEvent | null;
}

export default function AIDecisionPanel({ lastEvent }: AIDecisionPanelProps) {
  if (!lastEvent) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex items-center justify-center opacity-50 h-full">
        <span className="text-slate-500 font-mono text-xs">Waiting for AI inference loop...</span>
      </div>
    );
  }

  // Derive logic string
  const anomalyLevel = lastEvent.anomaly_score > 0.75 ? "Critical Anomaly" : lastEvent.anomaly_score > 0.4 ? "Moderate Anomaly" : "Low Anomaly";
  const riskLevel = lastEvent.user_risk_score > 0.75 ? "High Risk" : lastEvent.user_risk_score > 0.4 ? "Moderate Risk" : "Low Risk";
  const actionSummary = `${anomalyLevel} + ${riskLevel} → ${lastEvent.rl_action_name}`;

  return (
    <div className="bg-slate-900 border-l-[3px] border-l-purple-500 border-y border-r border-y-slate-800 border-r-slate-800 rounded-xl p-4 shadow-lg flex flex-col h-full relative overflow-hidden group">
      
      {/* Background glow effect */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>

      <div className="flex items-center gap-2 mb-4 relative z-10">
        <BrainCircuit size={18} className="text-purple-400" />
        <h3 className="text-purple-400 font-mono text-xs uppercase tracking-wider font-bold">RL Inference Engine Logic</h3>
      </div>

      <div className="space-y-3 relative z-10 flex-1">
        
        {/* Anomaly Bar */}
        <div>
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
            <span>DETECTION: Anomaly Score</span>
            <span className={lastEvent.anomaly_score > 0.6 ? "text-rose-400 font-bold" : ""}>{lastEvent.anomaly_score.toFixed(3)}</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-rose-500 transition-all duration-300" style={{width: `${lastEvent.anomaly_score * 100}%`}}></div>
          </div>
        </div>

        {/* Risk Bar */}
        <div>
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
            <span>UEBA: User Risk Score</span>
            <span className={lastEvent.user_risk_score > 0.6 ? "text-amber-400 font-bold" : ""}>{lastEvent.user_risk_score.toFixed(3)}</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div className="h-full bg-amber-500 transition-all duration-300" style={{width: `${lastEvent.user_risk_score * 100}%`}}></div>
          </div>
        </div>
        
        <div className="border-t border-slate-800 my-2"></div>

        {/* Severity Composite Bar */}
        <div>
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
            <span>COMPOSITE: Severity Core</span>
            <span className="text-cyan-400 font-bold">{lastEvent.severity_score.toFixed(3)}</span>
          </div>
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden shadow-inner">
            <div className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 transition-all duration-300" style={{width: `${lastEvent.severity_score * 100}%`}}></div>
          </div>
        </div>

      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/50 relative z-10 bg-slate-800/20 p-2 rounded flex justify-center items-center">
         <span className="text-xs font-mono text-purple-300 font-bold text-center tracking-wide">{actionSummary}</span>
      </div>

    </div>
  );
}
