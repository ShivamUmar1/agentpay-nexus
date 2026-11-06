import React from 'react';
import { 
  Bot, 
  Search, 
  BarChart3, 
  FileText, 
  CheckCircle2, 
  DollarSign, 
  CreditCard, 
  Compass, 
  Star, 
  Clock, 
  Check, 
  ArrowUpRight 
} from 'lucide-react';
import { Agent } from '../../types';

interface AgentCardProps {
  agent: Agent;
  onSelect: (agent: Agent) => void;
}

export const getAgentIcon = (iconName: string) => {
  switch (iconName) {
    case 'Search':
      return <Search className="w-5 h-5 text-cyan-400" />;
    case 'BarChart3':
      return <BarChart3 className="w-5 h-5 text-blue-400" />;
    case 'FileText':
      return <FileText className="w-5 h-5 text-violet-400" />;
    case 'CheckCircle2':
      return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
    case 'DollarSign':
      return <DollarSign className="w-5 h-5 text-amber-400" />;
    case 'CreditCard':
      return <CreditCard className="w-5 h-5 text-blue-300" />;
    case 'Compass':
      return <Compass className="w-5 h-5 text-indigo-400" />;
    default:
      return <Bot className="w-5 h-5 text-cyan-400" />;
  }
};

export const AgentCard: React.FC<AgentCardProps> = ({ agent, onSelect }) => {
  const isInternal = agent.pricing_model === 'internal' || agent.price === 0;

  return (
    <div className="glass-panel glass-panel-hover rounded-2xl p-5 flex flex-col justify-between relative group overflow-hidden border border-slate-800 hover:border-cyan-500/30">
      {/* Top row: Icon + Category + Status */}
      <div>
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-navy-800 border border-slate-700/60 flex items-center justify-center shadow-inner group-hover:scale-105 transition-transform duration-200">
            {getAgentIcon(agent.icon)}
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {agent.category}
            </span>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-amber-400">
              <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
              <span>{agent.rating.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Name & Description */}
        <h3 className="font-bold text-base text-white group-hover:text-cyan-300 transition-colors mb-2">
          {agent.name}
        </h3>
        <p className="text-slate-400 text-xs line-clamp-2 leading-relaxed mb-4">
          {agent.description}
        </p>

        {/* Capabilities Pills */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {agent.capabilities.slice(0, 3).map((cap, idx) => (
            <span
              key={idx}
              className="text-[10px] px-2 py-0.5 rounded bg-navy-950 text-slate-300 border border-slate-800 truncate max-w-[140px]"
            >
              {cap}
            </span>
          ))}
          {agent.capabilities.length > 3 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-navy-950 text-slate-500 border border-slate-800">
              +{agent.capabilities.length - 3}
            </span>
          )}
        </div>
      </div>

      {/* Bottom row: Pricing & Action Button */}
      <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between">
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono block">Service Fee</span>
          <div className="flex items-baseline gap-1">
            {isInternal ? (
              <span className="text-xs font-semibold text-emerald-400 font-mono">Platform Included</span>
            ) : (
              <>
                <span className="text-lg font-extrabold text-white font-mono">${agent.price.toFixed(2)}</span>
                <span className="text-[10px] text-slate-400 font-mono">USD/task</span>
              </>
            )}
          </div>
        </div>

        <button
          onClick={() => onSelect(agent)}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-cyan-500/20 text-slate-200 hover:text-cyan-300 border border-slate-700 hover:border-cyan-500/40 transition-all flex items-center gap-1"
        >
          <span>Inspect</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
