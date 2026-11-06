import React from 'react';
import { Bot, ShieldCheck, Heart, Github, ExternalLink, Cpu } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-800/80 bg-navy-950/60 mt-20 text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand Info */}
          <div className="space-y-3 md:col-span-1">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <span className="font-bold text-white tracking-tight">AgentPay Nexus</span>
            </div>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              Autonomous AI Agent Marketplace with intelligent service discovery, multi-agent collaboration, and official PayPal Sandbox settlement with human authorization.
            </p>
            <div className="flex items-center gap-2 text-[10px] text-cyan-400 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
              <span>PayPal AI Hackathon 2024-2026</span>
            </div>
          </div>

          {/* Architecture */}
          <div>
            <h4 className="text-slate-200 font-semibold mb-3 text-xs tracking-wider uppercase font-mono">Core Engine</h4>
            <ul className="space-y-2 text-[11px]">
              <li><span className="text-cyan-400 font-medium">Orchestrator:</span> Stateful LangGraph Plan</li>
              <li><span className="text-cyan-400 font-medium">Marketplace:</span> Dynamic Agent Discovery</li>
              <li><span className="text-cyan-400 font-medium">Data Analysis:</span> Deterministic CAGR & Charts</li>
              <li><span className="text-cyan-400 font-medium">Fact Audit:</span> QA Fact Grounding Gate</li>
              <li><span className="text-cyan-400 font-medium">Finance:</span> Immutable DB Ledger</li>
            </ul>
          </div>

          {/* Payment & Security */}
          <div>
            <h4 className="text-slate-200 font-semibold mb-3 text-xs tracking-wider uppercase font-mono">Payment Security</h4>
            <ul className="space-y-2 text-[11px]">
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>PayPal Orders v2 REST API</span>
              </li>
              <li>Server-side price verification</li>
              <li>Cryptographic capture verification</li>
              <li>Explicit user authorization gate</li>
              <li>No client-supplied fee trust</li>
            </ul>
          </div>

          {/* Stack & Links */}
          <div>
            <h4 className="text-slate-200 font-semibold mb-3 text-xs tracking-wider uppercase font-mono">Deployment</h4>
            <ul className="space-y-2 text-[11px]">
              <li>React 18 + Vite + Tailwind CSS</li>
              <li>FastAPI + Python 3.12 Backend</li>
              <li>Vercel Serverless Architecture</li>
              <li>PostgreSQL / Supabase Storage</li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px]">
          <p>© {new Date().getFullYear()} AgentPay Nexus. Built for PayPal Autonomous Commerce & Agentic AI.</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1 text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>PayPal Sandbox Verified</span>
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">Vercel Production Ready</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
