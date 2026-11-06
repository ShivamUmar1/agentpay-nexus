import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Layers, 
  ArrowUpRight, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  DollarSign, 
  Calendar,
  Loader2,
  Filter
} from 'lucide-react';
import { Task } from '../types';
import { api } from '../services/api';

export const TaskHistoryPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    async function fetchTasks() {
      try {
        setLoading(true);
        const res = await api.getTasks();
        setTasks(res.tasks);
      } catch (err) {
        console.error('Failed to load tasks:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchTasks();
  }, []);

  const filteredTasks = statusFilter === 'all' 
    ? tasks 
    : tasks.filter(t => t.status === statusFilter);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              EXECUTION ARCHIVE
            </span>
            <span className="text-xs text-slate-400 font-mono">{tasks.length} Total Pipelines</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Multi-Agent Workflows
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Browse and inspect all autonomous task execution graphs, audit trails, and unlocked deliverables.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 bg-navy-900 p-1 rounded-xl border border-slate-800 text-xs">
          {['all', 'completed', 'executing', 'awaiting_payment'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg capitalize transition-colors ${
                statusFilter === st
                  ? 'bg-cyan-500 text-navy-950 font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Tasks Grid / List */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          <span className="text-xs font-mono">Loading task archive...</span>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="py-20 text-center text-slate-500 text-sm">
          No workflows found for the selected filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTasks.map((t) => (
            <div
              key={t.id}
              className="glass-panel glass-panel-hover rounded-2xl p-5 border border-slate-800 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                    t.status === 'completed'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : t.status === 'awaiting_payment'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  }`}>
                    {t.status.replace('_', ' ')}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {new Date(t.created_at).toLocaleDateString()}
                  </span>
                </div>

                <h3 className="font-bold text-base text-white line-clamp-1 mb-2">
                  {t.title}
                </h3>
                <p className="text-slate-400 text-xs line-clamp-3 leading-relaxed mb-4">
                  {t.description}
                </p>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-500 font-mono block">SETTLED COST</span>
                  <span className="font-mono text-sm font-extrabold text-white">
                    ${t.total_cost.toFixed(2)} USD
                  </span>
                </div>

                <Link
                  to={`/tasks/${t.id}`}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-cyan-500/20 text-slate-200 hover:text-cyan-300 border border-slate-700 hover:border-cyan-500/40 transition-all flex items-center gap-1"
                >
                  <span>Open Studio</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
