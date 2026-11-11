import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Bot, 
  Sparkles, 
  DollarSign, 
  Sliders, 
  Send, 
  Loader2, 
  ShieldCheck, 
  Check, 
  Info,
  HelpCircle
} from 'lucide-react';
import { api } from '../services/api';

const PRESETS = [
  {
    title: "Electric Vehicle Market Research Report India",
    description: "Create a detailed market research report about the electric vehicle industry in India. Include market size, major competitors, future trends, opportunities, and a final investment analysis. My maximum budget is $10.",
    budget: 10.0,
    constraints: "Prioritize verified 2024 baselines, CAGR calculations, and battery localization policies."
  },
  {
    title: "Autonomous Agentic AI Payment Ecosystem",
    description: "Comprehensive competitive intelligence and architecture report analyzing AI agent economies, machine-to-machine micropayments, and fintech settlement frameworks.",
    budget: 12.0,
    constraints: "Include regulatory compliance notes, PayPal integration moats, and unit economics."
  },
  {
    title: "Global Clean Energy Storage M&A Analysis",
    description: "Evaluate lithium-iron-phosphate (LFP) vs sodium-ion commercial deployments, capital expenditure metrics, and key market consolidations across tier-1 energy producers.",
    budget: 15.0,
    constraints: "Provide 2024-2030 projection tables, supply chain bottlenecks, and risk matrices."
  }
];

export const CreateTaskPage: React.FC = () => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [budget, setBudget] = useState<string>('10.0');
  const [budgetError, setBudgetError] = useState<string | null>(null);
  const [constraints, setConstraints] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateBudget = (val: string): string | null => {
    const trimmed = val.trim();
    if (!trimmed) {
      return 'Maximum budget is required.';
    }
    const num = parseFloat(trimmed);
    if (isNaN(num) || !Number.isFinite(num)) {
      return 'Budget must be a valid numeric amount.';
    }
    if (num <= 0) {
      return 'Budget must be strictly greater than $0.00 USD.';
    }
    if (num > 1000.0) {
      return 'Budget cannot exceed the platform limit of $1,000.00 USD.';
    }
    return null;
  };

  const handleBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setBudget(val);
    setBudgetError(validateBudget(val));
  };

  const applyPreset = (preset: typeof PRESETS[0]) => {
    setTitle(preset.title);
    setDescription(preset.description);
    setBudget(preset.budget.toFixed(1));
    setBudgetError(null);
    setConstraints(preset.constraints);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError('Please provide both a task title and objective description.');
      return;
    }

    const bErr = validateBudget(budget);
    if (bErr) {
      setBudgetError(bErr);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const task = await api.createTask({
        title: title.trim(),
        description: description.trim(),
        budget: parseFloat(budget),
        currency: 'USD',
        constraints: constraints.trim() || undefined
      });
      navigate(`/tasks/${task.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to dispatch multi-agent task.');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
            WORKFLOW DISPATCH
          </span>
          <span className="text-xs text-slate-400 font-mono">Multi-Agent Orchestration</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Dispatch Autonomous Task
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Specify your research or analysis objective. The Nexus Orchestrator will formulate a stateful execution graph, match specialized marketplace agents, and execute within your budget.
        </p>
      </div>

      {/* Preset Selector */}
      <div>
        <span className="text-xs font-mono font-semibold uppercase text-slate-400 block mb-3 tracking-wider flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          Benchmark Demo Scenarios (One-Click Populate)
        </span>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {PRESETS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applyPreset(p)}
              className="text-left p-3.5 rounded-xl bg-navy-900 hover:bg-navy-850 border border-slate-800 hover:border-cyan-500/40 transition-all group"
            >
              <div className="flex items-center justify-between text-xs font-bold text-white group-hover:text-cyan-300 mb-1">
                <span className="truncate">{p.title}</span>
                <span className="font-mono text-cyan-400 shrink-0">${p.budget}</span>
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2">
                {p.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Main Task Form */}
      <form onSubmit={handleSubmit} className="glass-panel rounded-2xl p-6 sm:p-8 border border-slate-800 space-y-6">
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {/* Task Title */}
        <div>
          <label className="block text-xs font-mono font-semibold uppercase text-slate-300 mb-2">
            Task Objective Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Electric Vehicle Market Research Report India"
            required
            className="w-full px-4 py-2.5 rounded-xl bg-navy-950 border border-slate-800 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/60"
          />
        </div>

        {/* Detailed Objective */}
        <div>
          <label className="block text-xs font-mono font-semibold uppercase text-slate-300 mb-2">
            Detailed Objective & Requirements *
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
            placeholder="Describe the research scope, required market metrics, competitors to inspect, quantitative calculations, and deliverable format..."
            required
            className="w-full px-4 py-3 rounded-xl bg-navy-950 border border-slate-800 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/60 leading-relaxed"
          />
          <p className="text-[11px] text-slate-400 mt-1.5">
            The Orchestrator will decompose this description into subtasks for the Research, Analysis, Content, and QA agents.
          </p>
        </div>

        {/* Budget & Constraints Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Budget */}
          <div>
            <label className="block text-xs font-mono font-semibold uppercase text-slate-300 mb-2 flex items-center justify-between">
              <span>Maximum Budget Limit (USD) *</span>
              <span className="text-cyan-400 font-mono">
                ${!isNaN(parseFloat(budget)) && Number.isFinite(parseFloat(budget)) && parseFloat(budget) > 0 ? parseFloat(budget).toFixed(2) : '0.00'}
              </span>
            </label>
            <div className="relative">
              <DollarSign className={`w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 transition-colors ${
                budgetError ? 'text-rose-400' : 'text-slate-400'
              }`} />
              <input
                type="number"
                min="0.01"
                max="1000"
                step="0.5"
                value={budget}
                onChange={handleBudgetChange}
                placeholder="10.0"
                className={`w-full pl-9 pr-4 py-2.5 rounded-xl bg-navy-950 border text-sm font-mono text-white focus:outline-none transition-colors ${
                  budgetError
                    ? 'border-rose-500/80 focus:border-rose-500 text-rose-200'
                    : 'border-slate-800 focus:border-cyan-500/60'
                }`}
              />
            </div>
            {budgetError ? (
              <p className="text-[11px] text-rose-400 font-mono mt-1.5 flex items-center gap-1 animate-fadeIn">
                <span className="font-bold">⚠</span>
                <span>{budgetError}</span>
              </p>
            ) : (
              <p className="text-[11px] text-slate-400 mt-1">
                Standard 4-agent research pipeline costs $8.00 USD (platform max $1,000.00).
              </p>
            )}
          </div>

          {/* Constraints */}
          <div>
            <label className="block text-xs font-mono font-semibold uppercase text-slate-300 mb-2">
              Specific Constraints or Milestones (Optional)
            </label>
            <input
              type="text"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              placeholder="e.g. Focus on TCO fleet economics, 2024 data only"
              className="w-full px-4 py-2.5 rounded-xl bg-navy-950 border border-slate-800 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/60"
            />
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Human Payment Approval Required Before Charge</span>
          </div>

          <button
            type="submit"
            disabled={loading || Boolean(budgetError) || !budget.trim() || parseFloat(budget) <= 0}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-bold text-sm flex items-center gap-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50 transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Formulating Multi-Agent Plan...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4 stroke-[2.5]" />
                <span>Submit & Initialize Graph</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
