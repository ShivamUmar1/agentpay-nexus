import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Bot, 
  Layers, 
  Activity, 
  DollarSign, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight, 
  PlusCircle, 
  CreditCard, 
  ShieldCheck,
  TrendingUp,
  Loader2
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { Task, Transaction, Agent } from '../types';
import { api } from '../services/api';

export const Dashboard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [agentsCount, setAgentsCount] = useState<number>(8);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        const [tasksRes, txsRes, agentsRes] = await Promise.all([
          api.getTasks(),
          api.getTransactions(),
          api.getAgents()
        ]);
        setTasks(tasksRes.tasks);
        setTransactions(txsRes);
        setAgentsCount(agentsRes.total);
      } catch (err) {
        console.error('Failed to load dashboard:', err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  const totalTasks = tasks.length;
  const activeTasks = tasks.filter(t => t.status === 'executing' || t.status === 'planning' || t.status === 'awaiting_payment').length;
  const completedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'paid').length;
  const totalSpent = transactions.reduce((acc, tx) => acc + (tx.amount || 0), 0);

  // Activity chart data
  const activityData = [
    { name: 'Mon', tasks: 2, spend: 16.0 },
    { name: 'Tue', tasks: 4, spend: 32.0 },
    { name: 'Wed', tasks: 3, spend: 24.0 },
    { name: 'Thu', tasks: 5, spend: 40.0 },
    { name: 'Fri', tasks: totalTasks > 0 ? totalTasks : 3, spend: totalSpent > 0 ? totalSpent : 24.0 },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              OPERATIONS CONSOLE
            </span>
            <span className="text-xs text-slate-400 font-mono">Real-Time Ledger</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Autonomous Commerce Dashboard
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Monitor stateful agent orchestration pipelines, verified deliverables, and PayPal Sandbox transactions.
          </p>
        </div>

        <Link
          to="/create"
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-bold text-sm flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all self-start sm:self-auto"
        >
          <PlusCircle className="w-4 h-4 stroke-[2.5]" />
          <span>Dispatch New Task</span>
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1 */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-mono uppercase">Total Workflows</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{totalTasks}</span>
            <span className="text-xs text-slate-500 font-mono">dispatched</span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-mono uppercase">Active Pipelines</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-blue-400 font-mono">{activeTasks}</span>
            <span className="text-xs text-slate-500 font-mono">running</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-mono uppercase">Completed & Verified</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-400 font-mono">{completedTasks}</span>
            <span className="text-xs text-slate-500 font-mono">delivered</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-mono uppercase">Marketplace Spend</span>
            <DollarSign className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">${totalSpent.toFixed(2)}</span>
            <span className="text-xs text-slate-500 font-mono">USD</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Tasks Table & Activity Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column (8 cols): Tasks Table */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-mono font-semibold uppercase text-slate-300 tracking-wider">
              Recent Multi-Agent Pipelines
            </h3>
            <Link to="/tasks" className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1">
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
            {tasks.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-xs">
                No active workflows yet. Launch your first task above.
              </div>
            ) : (
              <div className="divide-y divide-slate-800/80">
                {tasks.slice(0, 5).map((t) => (
                  <div key={t.id} className="p-4 hover:bg-slate-800/30 transition-colors flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
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
                      <h4 className="text-sm font-bold text-white truncate">{t.title}</h4>
                      <p className="text-xs text-slate-400 truncate mt-0.5">{t.description}</p>
                    </div>

                    <div className="text-right shrink-0 flex items-center gap-4">
                      <div>
                        <span className="text-sm font-extrabold text-white font-mono block">
                          ${t.total_cost.toFixed(2)}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">Max ${t.budget.toFixed(2)}</span>
                      </div>

                      <Link
                        to={`/tasks/${t.id}`}
                        className="p-2 rounded-lg bg-navy-800 hover:bg-cyan-500/20 text-slate-300 hover:text-cyan-300 border border-slate-700 transition-colors"
                      >
                        <ArrowUpRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (4 cols): PayPal Transactions Feed */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-mono font-semibold uppercase text-slate-300 tracking-wider">
              Settlement Ledger
            </h3>
            <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              Verified
            </span>
          </div>

          <div className="glass-panel rounded-2xl border border-slate-800 p-4 space-y-3 font-mono text-xs">
            {transactions.length === 0 ? (
              <div className="py-8 text-center text-slate-500 italic text-[11px]">
                No payment transactions recorded yet.
              </div>
            ) : (
              transactions.slice(0, 5).map((tx) => (
                <div key={tx.id} className="p-3 rounded-xl bg-navy-950/80 border border-slate-800/80 space-y-1.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400 truncate max-w-[140px]">
                      {tx.paypal_order_id || tx.id.slice(0, 12)}
                    </span>
                    <span className="font-bold text-emerald-400">
                      ${tx.amount.toFixed(2)} {tx.currency}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span className="capitalize">{tx.provider.replace('_', ' ')}</span>
                    <span>{new Date(tx.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
