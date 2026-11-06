import React from 'react';
import { 
  X, 
  Star, 
  CheckCircle, 
  Clock, 
  Shield, 
  Zap, 
  Award,
  Layers
} from 'lucide-react';
import { Agent } from '../../types';
import { getAgentIcon } from './AgentCard';

interface AgentDetailModalProps {
  agent: Agent | null;
  onClose: () => void;
}

export const AgentDetailModal: React.FC<AgentDetailModalProps> = ({ agent, onClose }) => {
  if (!agent) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-2xl bg-navy-900 border border-slate-700/80 shadow-2xl overflow-hidden p-6 text-slate-100 max-h-[90vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-16 h-16 rounded-2xl bg-navy-800 border border-slate-700 flex items-center justify-center shadow-lg">
            {getAgentIcon(agent.icon)}
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                {agent.category}
              </span>
              <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                {agent.availability}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white">{agent.name}</h2>
            <div className="flex items-center gap-4 text-xs text-slate-400 mt-1 font-mono">
              <span className="flex items-center gap-1 text-amber-400">
                <Star className="w-3.5 h-3.5 fill-amber-400" />
                {agent.rating.toFixed(2)} Rating
              </span>
              <span>•</span>
              <span>{agent.completed_tasks} Tasks Completed</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {agent.estimated_time} avg
              </span>
            </div>
          </div>
        </div>

        {/* Overview */}
        <div className="space-y-6">
          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono mb-2">Description</h4>
            <p className="text-sm text-slate-300 leading-relaxed bg-navy-950/60 p-3.5 rounded-xl border border-slate-800">
              {agent.description}
            </p>
          </div>

          {/* Pricing Model Card */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-navy-950/60 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-400 font-mono block mb-1">Pricing Model</span>
              <span className="text-sm font-bold text-white uppercase font-mono">{agent.pricing_model}</span>
              <p className="text-[11px] text-slate-400 mt-0.5">Calculated per task node execution</p>
            </div>
            <div className="bg-navy-950/60 p-3.5 rounded-xl border border-slate-800">
              <span className="text-[11px] text-slate-400 font-mono block mb-1">Standard Rate</span>
              <span className="text-base font-extrabold text-cyan-400 font-mono">
                {agent.price === 0 ? 'Platform Core (Free)' : `$${agent.price.toFixed(2)} USD`}
              </span>
              <p className="text-[11px] text-slate-400 mt-0.5">Fixed rate from trusted database ledger</p>
            </div>
          </div>

          {/* Capabilities */}
          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono mb-2 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              Specialized Capabilities
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {agent.capabilities.map((cap, i) => (
                <div key={i} className="flex items-center gap-2 p-2.5 rounded-lg bg-navy-950/80 border border-slate-800 text-xs text-slate-200">
                  <CheckCircle className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                  <span>{cap}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Supported Tasks */}
          <div>
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              Supported Workflow Scenarios
            </h4>
            <div className="flex flex-wrap gap-2">
              {agent.supported_tasks.map((task, i) => (
                <span key={i} className="text-xs font-mono px-3 py-1 rounded-full bg-blue-950/40 text-blue-300 border border-blue-500/30">
                  #{task}
                </span>
              ))}
            </div>
          </div>

          {/* Footer actions */}
          <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-400 font-mono">Agent ID: {agent.id}</span>
            <button
              onClick={onClose}
              className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
