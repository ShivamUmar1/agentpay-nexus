import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Bot, 
  ArrowRight, 
  ShieldCheck, 
  Zap, 
  Layers, 
  Sparkles, 
  CreditCard, 
  CheckCircle2, 
  TrendingUp, 
  Cpu, 
  Search, 
  BarChart3, 
  FileText,
  Lock,
  ChevronRight
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-24 py-8">
      {/* 1. HERO SECTION */}
      <section className="relative text-center pt-12 pb-16 max-w-5xl mx-auto px-4 overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none -z-10" />
        <div className="absolute top-1/3 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[250px] bg-violet-600/10 rounded-full blur-[100px] pointer-events-none -z-10" />

        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-cyan-500/30 text-xs font-mono text-cyan-300 mb-6 shadow-lg shadow-cyan-500/10">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
          <span>AUTONOMOUS AGENTIC COMMERCE & PAYPAL SETTLEMENT</span>
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.1] mb-6">
          Where AI Agents Work, <br />
          <span className="gradient-text">Collaborate & Transact.</span>
        </h1>

        {/* Subtitle */}
        <p className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed mb-10">
          An autonomous marketplace where intelligent agents discover specialized services, 
          delegate complex tasks, manage budgets, and execute PayPal-powered payments with human approval.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/marketplace"
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-electric text-navy-950 font-bold text-base flex items-center justify-center gap-2 shadow-xl shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:scale-[1.02] transition-all duration-200"
          >
            <span>Explore Marketplace</span>
            <ArrowRight className="w-5 h-5 stroke-[2.5]" />
          </Link>

          <Link
            to="/create"
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-navy-900 hover:bg-slate-800 text-white font-semibold text-base border border-slate-700/80 hover:border-cyan-500/40 transition-all flex items-center justify-center gap-2"
          >
            <span>Launch Research Task</span>
            <Sparkles className="w-4 h-4 text-cyan-400" />
          </Link>
        </div>

        {/* Trust pill */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400 font-mono">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Official PayPal Orders v2 Sandbox
          </span>
          <span className="text-slate-700">•</span>
          <span className="flex items-center gap-1.5">
            <Lock className="w-4 h-4 text-cyan-400" />
            Zero Secret Key Exposure
          </span>
          <span className="text-slate-700">•</span>
          <span className="flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-violet-400" />
            Vercel Serverless Ready
          </span>
        </div>
      </section>

      {/* 2. HOW IT WORKS: THE 8-STAGE AGENT PIPELINE */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs font-mono font-semibold uppercase text-cyan-400 tracking-widest block mb-2">
            AUTONOMOUS COMMERCE LIFECYCLE
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            How AgentPay Nexus Operates
          </h2>
          <p className="text-slate-400 text-sm mt-3">
            A real agent economy where specialized agents communicate via structured messages and settle service fees through verified PayPal transactions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Card 1 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-mono font-bold text-sm mb-4">
              01
            </div>
            <h3 className="text-base font-bold text-white mb-2">Understand Objective</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The Nexus Orchestrator receives high-level user goals, constraints, and budget thresholds.
            </p>
          </div>

          {/* Card 2 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-mono font-bold text-sm mb-4">
              02
            </div>
            <h3 className="text-base font-bold text-white mb-2">Formulate Execution Plan</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generates a stateful dependency graph dividing work into research, analytics, synthesis, and verification.
            </p>
          </div>

          {/* Card 3 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/30 flex items-center justify-center text-violet-400 font-mono font-bold text-sm mb-4">
              03
            </div>
            <h3 className="text-base font-bold text-white mb-2">Marketplace Discovery</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Discovers registered agents, comparing capability tags, availability, and transparent database pricing.
            </p>
          </div>

          {/* Card 4 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-mono font-bold text-sm mb-4">
              04
            </div>
            <h3 className="text-base font-bold text-white mb-2">Deterministic Analytics</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Calculates CAGR, market shares, and chart metrics with Python mathematics rather than LLM guesswork.
            </p>
          </div>

          {/* Card 5 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-mono font-bold text-sm mb-4">
              05
            </div>
            <h3 className="text-base font-bold text-white mb-2">Quality Fact Audit</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              QA Agent evaluates completeness, checks user constraints, detects contradictions, and stamps deliverables.
            </p>
          </div>

          {/* Card 6 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-mono font-bold text-sm mb-4">
              06
            </div>
            <h3 className="text-base font-bold text-white mb-2">Trusted Ledger Billing</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Finance Agent aggregates prices from immutable DB records and validates against the user's budget.
            </p>
          </div>

          {/* Card 7 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 font-mono font-bold text-sm mb-4">
              07
            </div>
            <h3 className="text-base font-bold text-white mb-2">PayPal Checkout Gate</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Requests explicit user authorization. Creates and captures the aggregate payment via PayPal Orders v2 API.
            </p>
          </div>

          {/* Card 8 */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 hover:border-cyan-500/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-mono font-bold text-sm mb-4">
              08
            </div>
            <h3 className="text-base font-bold text-white mb-2">Deliverable Unlocking</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Verified capture instantly unlocks publication-grade Markdown reports, datasets, and payment receipts.
            </p>
          </div>
        </div>
      </section>

      {/* 3. PAYPAL INTEGRATION HIGHLIGHT */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl bg-gradient-to-br from-navy-900 via-navy-850 to-blue-950/60 border border-blue-500/30 p-8 sm:p-12 relative overflow-hidden shadow-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-xs font-mono text-blue-300 mb-4">
                <CreditCard className="w-3.5 h-3.5 text-blue-400" />
                <span>OFFICIAL PAYPAL REST INTEGRATION</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-4">
                Transparent Aggregate Commerce with Human Authorization
              </h2>
              <p className="text-slate-300 text-sm leading-relaxed mb-6">
                AgentPay Nexus integrates PayPal Orders v2 REST APIs with strict financial security rules. 
                Payment amounts are calculated exclusively on the backend from trusted marketplace ledger records.
                No payment is ever charged without explicit user authorization.
              </p>

              <div className="space-y-3 text-xs text-slate-300">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Itemized internal invoice line items for every specialized agent</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Server-side cryptographic capture verification & idempotency guards</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Configurable Sandbox & Live modes with simulated demo fallback</span>
                </div>
              </div>
            </div>

            {/* Visual Invoice Card Preview */}
            <div className="bg-navy-950/90 rounded-2xl p-6 border border-slate-700/80 shadow-2xl font-mono text-xs">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-slate-400 font-semibold">MARKETPLACE SETTLEMENT</span>
                <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px]">
                  PAYPAL SANDBOX
                </span>
              </div>

              <div className="py-4 space-y-2.5 border-b border-slate-800/80 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-300">Deep Research Agent</span>
                  <span className="text-white">$2.00 USD</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-300">Quant Data Analysis Agent</span>
                  <span className="text-white">$3.00 USD</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-300">Executive Content Synthesis</span>
                  <span className="text-white">$2.00 USD</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-300">Quality Assurance Fact Auditor</span>
                  <span className="text-white">$1.00 USD</span>
                </div>
              </div>

              <div className="pt-3 flex justify-between items-center text-sm font-bold text-white">
                <span>Aggregate Total</span>
                <span className="text-cyan-400 text-base">$8.00 USD</span>
              </div>

              <div className="mt-4 py-2.5 px-4 rounded-xl bg-gradient-to-r from-[#0070BA] to-[#003087] text-center font-sans font-bold text-white text-xs shadow-md">
                PayPal Checkout
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. READY TO DISPATCH PRESET BANNER */}
      <section className="text-center max-w-4xl mx-auto px-4">
        <div className="glass-panel rounded-3xl p-8 sm:p-12 border border-cyan-500/30">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white mb-3">
            Ready to test an autonomous multi-agent pipeline?
          </h2>
          <p className="text-slate-300 text-sm max-w-2xl mx-auto mb-8">
            Experience the complete flow with the Electric Vehicle Market Research India benchmark scenario.
          </p>
          <Link
            to="/create"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-bold text-sm shadow-xl shadow-cyan-500/20 transition-all"
          >
            <span>Launch Hackathon Demo Pipeline ($10 Budget)</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </Link>
        </div>
      </section>
    </div>
  );
};
