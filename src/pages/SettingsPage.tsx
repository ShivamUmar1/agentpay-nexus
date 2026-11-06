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
  Server,
  Zap,
  Clock,
  HelpCircle
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
              LIVE SYSTEM CONSOLE
            </span>
            <span className="text-xs text-slate-400 font-mono">Platform Health & Real Integrations</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Diagnostics & Integrations
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Real-time verification of Google Gemini reasoning, PayPal Sandbox payment gateway, and Supabase persistent PostgreSQL storage.
          </p>
        </div>

        <button
          onClick={fetchStatus}
          disabled={loading}
          className="p-2.5 rounded-xl bg-navy-900 border border-slate-800 text-slate-300 hover:text-cyan-400 hover:border-cyan-500/40 transition-colors flex items-center gap-2 text-xs font-mono"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Probing...' : 'Re-Probe'}
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
            {status?.ai_orchestration?.status === 'connected' ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> CONNECTED
              </span>
            ) : status?.ai_orchestration?.status === 'error' ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> ERROR
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                <HelpCircle className="w-3 h-3" /> DEMO FALLBACK
              </span>
            )}
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">Google Gemini AI Engine</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Provider: <span className="text-cyan-400 font-bold uppercase">{status?.ai_orchestration?.provider || 'Checking...'}</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              Model: <span className="text-slate-300">{status?.ai_orchestration?.model || 'gemini-2.0-flash'}</span>
            </p>
            {status?.ai_orchestration?.latency_ms && (
              <p className="text-[10px] text-emerald-400 font-mono mt-1 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" /> Latency: {status.ai_orchestration.latency_ms}ms
              </p>
            )}
            {status?.ai_orchestration?.error && (
              <p className="text-[10px] text-rose-400 font-mono mt-1 break-words">
                {status.ai_orchestration.error}
              </p>
            )}
          </div>
        </div>

        {/* 2. PayPal Sandbox */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <CreditCard className="w-5 h-5" />
            </div>
            {status?.payment_gateway?.status === 'sandbox_connected' ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> SANDBOX LIVE
              </span>
            ) : status?.payment_gateway?.status === 'auth_failed' ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> AUTH FAILED
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                <HelpCircle className="w-3 h-3" /> DEMO GATEWAY
              </span>
            )}
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">PayPal Sandbox REST API</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Gateway: <span className="text-blue-400 font-bold">Orders v2 REST</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              Status: <span className="text-slate-300">{status?.payment_gateway?.status || 'Probing...'}</span>
            </p>
            {status?.payment_gateway?.client_id && (
              <p className="text-[10px] text-slate-400 font-mono mt-1">
                App ID: {status.payment_gateway.client_id}
              </p>
            )}
            {status?.payment_gateway?.latency_ms && (
              <p className="text-[10px] text-emerald-400 font-mono mt-1 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" /> OAuth Ping: {status.payment_gateway.latency_ms}ms
              </p>
            )}
            {status?.payment_gateway?.error && (
              <p className="text-[10px] text-rose-400 font-mono mt-1 break-words">
                {status.payment_gateway.error}
              </p>
            )}
          </div>
        </div>

        {/* 3. Database */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center text-violet-400">
              <Database className="w-5 h-5" />
            </div>
            {status?.database?.persistent ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> SUPABASE PG
              </span>
            ) : status?.database?.status === 'connected' ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> EPHEMERAL SQLITE
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> DB ERROR
              </span>
            )}
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">Persistent DB Ledger</h3>
            <p className="text-xs text-slate-400 font-mono mt-1">
              Engine: <span className="text-violet-400 font-bold uppercase">{status?.database?.type || 'Probing...'}</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              Tier: <span className="text-slate-300">{status?.database?.hosted || 'local'}</span>
            </p>
            {status?.database?.counts && (
              <p className="text-[10px] text-slate-400 font-mono mt-1">
                Ledger: {status.database.counts.agents} agents | {status.database.counts.tasks} tasks | {status.database.counts.transactions} txs
              </p>
            )}
            {status?.database?.latency_ms && (
              <p className="text-[10px] text-emerald-400 font-mono mt-1 flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" /> Query: {status.database.latency_ms}ms
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Security & Financial Integrity Rules */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="text-sm font-mono font-semibold uppercase text-slate-300 tracking-wider flex items-center gap-2">
          <Lock className="w-4 h-4 text-cyan-400" />
          Production Integration Architecture
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
              All workflow progress is persisted to Supabase PostgreSQL. Browser reloads or serverless invocations resume cleanly without state loss.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
