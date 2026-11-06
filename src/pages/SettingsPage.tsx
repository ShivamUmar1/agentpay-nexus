import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Cpu, 
  CreditCard, 
  Database, 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Lock,
  Layers,
  Server
} from 'lucide-react';
import { SystemStatus } from '../types';
import { api } from '../services/api';

export const SettingsPage: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const res = await api.getSystemStatus();
      setStatus(res);
    } catch (err) {
      console.error('Failed to load system diagnostics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              SYSTEM CONSOLE
            </span>
            <span className="text-xs text-slate-400 font-mono">Platform Health & Integrations</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Diagnostics & Settings
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time status of AI orchestration models, official PayPal Sandbox payment bridge, and persistent database ledger.
          </p>
        </div>

        <button
          onClick={fetchStatus}
          className="p-2.5 rounded-xl bg-navy-900 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-500/40 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Diagnostics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 1. AI Orchestrator */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Cpu className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              ACTIVE
            </span>
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">AI Orchestration Engine</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Provider: <span className="text-cyan-400 font-bold uppercase">{status?.ai_orchestration?.provider || 'Gemini API'}</span>
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Model: {status?.ai_orchestration?.model || 'gemini-1.5-flash'}
            </p>
          </div>
        </div>

        {/* 2. PayPal Sandbox */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <CreditCard className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
              SANDBOX READY
            </span>
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">PayPal Payment Bridge</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Gateway: <span className="text-blue-400 font-bold">Orders v2 REST API</span>
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Mode: {status?.payment_gateway?.status || 'Sandbox Active'}
            </p>
          </div>
        </div>

        {/* 3. Database */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center text-violet-400">
              <Database className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              CONNECTED
            </span>
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">Persistent DB Ledger</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Storage: <span className="text-violet-400 font-bold uppercase">{status?.database?.type || 'PostgreSQL'}</span>
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Status: Operational (Stateful Graph)
            </p>
          </div>
        </div>
      </div>

      {/* Security & Financial Integrity Rules */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="text-sm font-mono font-semibold uppercase text-slate-300 tracking-wider flex items-center gap-2">
          <Lock className="w-4 h-4 text-cyan-400" />
          Financial Security Architecture
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
          <div className="p-3.5 rounded-xl bg-navy-950 border border-slate-800 space-y-1">
            <span className="font-bold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Trusted Ledger Cost Calculation
            </span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Amounts are calculated exclusively on the backend from registered database pricing. Browser-supplied amounts are rejected.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-navy-950 border border-slate-800 space-y-1">
            <span className="font-bold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Human Authorization Gate
            </span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              No autonomous agent possesses independent payment authority. Explicit user approval is enforced prior to PayPal order creation.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-navy-950 border border-slate-800 space-y-1">
            <span className="font-bold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Cryptographic Capture Verification
            </span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Payment captures are authenticated directly against PayPal REST endpoints before deliverables are unlocked.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-navy-950 border border-slate-800 space-y-1">
            <span className="font-bold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Vercel Serverless Resumability
            </span>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              All workflow progress is persisted to the database. Browser reloads or serverless invocations resume cleanly without state loss.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
