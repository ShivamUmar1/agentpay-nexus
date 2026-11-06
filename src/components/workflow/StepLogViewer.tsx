import React from 'react';
import { Terminal, Shield, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { ActivityLog } from '../../types';

interface StepLogViewerProps {
  logs: ActivityLog[];
}

export const StepLogViewer: React.FC<StepLogViewerProps> = ({ logs }) => {
  const getEventBadge = (type: string) => {
    switch (type) {
      case 'plan':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-blue-500/20 text-blue-300 border border-blue-500/30">PLAN</span>;
      case 'execute':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">EXEC</span>;
      case 'review':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">AUDIT</span>;
      case 'finance':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">LEDGER</span>;
      case 'payment':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">PAYPAL</span>;
      case 'error':
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30">ERROR</span>;
      default:
        return <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-800 text-slate-400 border border-slate-700">SYS</span>;
    }
  };

  return (
    <div className="rounded-2xl bg-navy-950 border border-slate-800 overflow-hidden font-mono text-xs flex flex-col h-full max-h-[380px]">
      {/* Terminal Title Bar */}
      <div className="bg-navy-900 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-300">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-xs tracking-wider">AGENT OBSERVABILITY LOG</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
        </div>
      </div>

      {/* Log Feed */}
      <div className="p-4 overflow-y-auto space-y-2.5 flex-1 divide-y divide-slate-800/40">
        {logs.length === 0 ? (
          <div className="py-8 text-center text-slate-500 italic text-[11px]">
            Awaiting agent execution events...
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="pt-2 first:pt-0 flex items-start gap-2.5 text-[11px] leading-relaxed">
              <span className="text-slate-500 shrink-0 select-none text-[10px]">
                {new Date(log.created_at).toLocaleTimeString()}
              </span>
              <div className="shrink-0">{getEventBadge(log.event_type)}</div>
              <div className="text-slate-300 flex-1">
                {log.agent_id && (
                  <span className="text-cyan-400/90 font-semibold mr-1.5">
                    [{log.agent_id}]:
                  </span>
                )}
                <span>{log.message}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
