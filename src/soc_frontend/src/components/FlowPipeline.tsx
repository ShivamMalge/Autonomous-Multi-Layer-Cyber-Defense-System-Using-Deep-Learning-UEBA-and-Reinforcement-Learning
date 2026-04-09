import React from 'react';
import { SOCEvent } from '../hooks/useWebSocket';
import { Database, Activity, User, Brain, ShieldAlert, Zap } from 'lucide-react';

interface FlowPipelineProps {
  lastEvent: SOCEvent | null;
}

export default function FlowPipeline({ lastEvent }: FlowPipelineProps) {
  if (!lastEvent) {
    return (
      <div className="bg-[#111826] border border-slate-800 rounded-xl p-6 h-full flex flex-col items-center justify-center">
        <span className="text-slate-500 text-sm">System Idle. Waiting for telemetry...</span>
      </div>
    );
  }

  const nodes = [
    {
      id: 0, title: "Input", icon: <Database size={24} />,
      info: lastEvent.ip, val: lastEvent.user_id, active: true
    },
    {
      id: 1, title: "IDS", icon: <Activity size={24} />,
      info: "Anomaly", val: lastEvent.anomaly_score.toFixed(2), 
      warn: lastEvent.anomaly_score > 0.6
    },
    {
      id: 2, title: "UEBA", icon: <User size={24} />,
      info: "Risk", val: lastEvent.user_risk_score.toFixed(2),
      warn: lastEvent.user_risk_score > 0.6
    },
    {
      id: 3, title: "RL Agent", icon: <Brain size={24} />,
      info: "Action", val: lastEvent.rl_action_name, active: true
    },
    {
      id: 4, title: "System", icon: <ShieldAlert size={24} />,
      info: "State", val: lastEvent.was_downgraded ? "OVERRIDE" : "APPROVED",
      warn: lastEvent.was_downgraded
    },
    {
      id: 5, title: "Output", icon: <Zap size={24} />,
      info: "Final", val: lastEvent.final_action_name,
      severe: lastEvent.final_action_name !== "MONITOR"
    }
  ];

  return (
    <div className="bg-[#111826] border border-slate-800 rounded-xl p-8 h-full flex flex-col relative shadow-sm">
      <h2 className="text-slate-400 font-semibold text-sm uppercase tracking-wider mb-8">Pipeline Activity</h2>
      
      {/* Background Line */}
      <div className="absolute top-[60%] left-12 right-12 h-px bg-slate-800 z-0" />

      <div className="flex-1 flex justify-between items-center relative z-10">
        {nodes.map((node, i) => {
          let badgeColor = "text-slate-300";
          if (node.warn) badgeColor = "text-amber-400 font-medium";
          if (node.severe) badgeColor = "text-rose-400 font-medium";
          
          return (
            <div key={node.title} className="flex flex-col items-center bg-[#0B0F14] border border-slate-800 p-4 rounded-xl w-32 shadow-sm transition-transform hover:-translate-y-1 duration-300 ease-out">
              <div className="text-slate-400 mb-2">{node.icon}</div>
              <div className="text-[11px] text-slate-500 uppercase tracking-wide mb-3">{node.title}</div>
              
              <div className="text-center">
                <div className="text-[10px] text-slate-500">{node.info}</div>
                <div className={`text-xs mt-1 truncate w-full px-1 ${badgeColor}`}>{node.val}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  );
}
