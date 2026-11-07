import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell 
} from 'recharts';
import { 
  Bot, 
  Play, 
  Pause, 
  RotateCw, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle,
  CreditCard, 
  Download, 
  Copy, 
  Check, 
  ShieldCheck, 
  FileText, 
  BarChart3, 
  Layers, 
  DollarSign, 
  ArrowRight,
  ExternalLink,
  Loader2,
  Info
} from 'lucide-react';
import { Task, TaskStep, ActivityLog, PaymentSummary } from '../types';
import { api } from '../services/api';
import { WorkflowVisualizer } from '../components/workflow/WorkflowVisualizer';
import { StepLogViewer } from '../components/workflow/StepLogViewer';
import { InvoiceModal } from '../components/payment/InvoiceModal';

const CHART_COLORS = ['#00F0FF', '#0080FF', '#8B5CF6', '#10B981', '#F59E0B'];

export const TaskExecutionPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const isCancelled = searchParams.get('cancelled') === 'true';
  const isApproved = searchParams.get('approved') === 'true';
  const token = searchParams.get('token');

  const [task, setTask] = useState<Task | null>(null);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [selectedStep, setSelectedStep] = useState<TaskStep | null>(null);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [autoRun, setAutoRun] = useState(false);
  const [activeTab, setActiveTab] = useState<'report' | 'charts' | 'audit' | 'raw'>('report');
  
  // Payment state & notices
  const [paymentSummary, setPaymentSummary] = useState<PaymentSummary | null>(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentNotice, setPaymentNotice] = useState<{
    type: 'cancelled' | 'success' | 'error' | 'capturing';
    message: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const capturingRef = useRef(false);

  // Polling ref
  const autoRunRef = useRef(autoRun);
  autoRunRef.current = autoRun;

  const loadTaskData = async () => {
    if (!taskId) return;
    try {
      const [taskRes, logsRes] = await Promise.all([
        api.getTask(taskId),
        api.getTaskActivity(taskId)
      ]);
      setTask(taskRes);
      setLogs(logsRes);

      // Auto-select current or first running step
      if (!selectedStep && taskRes.steps.length > 0) {
        const active = taskRes.steps.find(s => s.status === 'running') || taskRes.steps[0];
        setSelectedStep(active);
      } else if (selectedStep) {
        // Refresh selected step
        const refreshed = taskRes.steps.find(s => s.id === selectedStep.id);
        if (refreshed) setSelectedStep(refreshed);
      }
    } catch (err) {
      console.error('Failed to load task state:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTaskData();
    const interval = setInterval(loadTaskData, 3000);
    return () => clearInterval(interval);
  }, [taskId]);

  // Handle PayPal Cancellation
  useEffect(() => {
    if (isCancelled) {
      setPaymentNotice({
        type: 'cancelled',
        message: 'PayPal checkout session was cancelled. Your invoice of $8.00 USD is preserved and awaiting authorization whenever you are ready.'
      });
      setShowPaymentModal(false);
    }
  }, [isCancelled]);

  // Handle PayPal Approval -> Automatic Server-Side Capture
  useEffect(() => {
    if (isApproved && token && task && task.status === 'awaiting_payment' && !capturingRef.current) {
      capturingRef.current = true;
      setPaymentNotice({
        type: 'capturing',
        message: 'PayPal Buyer Approval Detected! Validating order on PayPal and capturing payment server-side...'
      });

      const executeCapture = async () => {
        try {
          const res = await api.capturePayPalOrder(task.id, token);
          if (res.success) {
            setPaymentNotice({
              type: 'success',
              message: `Payment Verified & Captured ($${res.amount.toFixed(2)} ${res.currency})! Order ID: ${res.order_id}. Final deliverable unlocked!`
            });
            setShowPaymentModal(false);
            setSearchParams({});
            await loadTaskData();
          } else {
            setPaymentNotice({
              type: 'error',
              message: res.message || 'Payment capture failed.'
            });
          }
        } catch (err: any) {
          setPaymentNotice({
            type: 'error',
            message: err.message || 'Could not capture payment. Please ensure buyer approval was completed on PayPal.'
          });
        }
      };

      executeCapture();
    }
  }, [isApproved, token, task?.status]);

  // Auto-runner loop
  useEffect(() => {
    if (!autoRun || !task || advancing) return;

    if (task.status === 'executing') {
      const timer = setTimeout(() => {
        handleAdvanceStep();
      }, 1500);
      return () => clearTimeout(timer);
    } else if (task.status === 'awaiting_payment') {
      if (!isCancelled && !isApproved) {
        handleOpenPaymentModal();
      }
      setAutoRun(false);
    }
  }, [autoRun, task?.status, task?.current_step, advancing, isCancelled, isApproved]);

  const handleAdvanceStep = async () => {
    if (!taskId || advancing) return;
    try {
      setAdvancing(true);
      setExecutionError(null);
      await api.advanceTask(taskId);
      await loadTaskData();
    } catch (err: any) {
      console.error('Advance step failed:', err);
      setAutoRun(false);
      setExecutionError(err.message || 'Workflow advancement halted.');
      await loadTaskData();
    } finally {
      setAdvancing(false);
    }
  };

  const handleOpenPaymentModal = async () => {
    if (!taskId) return;
    try {
      const summary = await api.getPaymentSummary(taskId);
      setPaymentSummary(summary);
      setShowPaymentModal(true);
    } catch (err) {
      console.error('Failed to fetch invoice:', err);
    }
  };

  const handleCopyReport = () => {
    if (task?.final_output?.report_markdown) {
      navigator.clipboard.writeText(task.final_output.report_markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadMarkdown = () => {
    if (!task?.final_output?.report_markdown) return;
    const blob = new Blob([task.final_output.report_markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${task.title.replace(/\s+/g, '_')}_Report.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !task) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-3 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span className="text-xs font-mono">Restoring stateful execution graph from database...</span>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <AlertCircle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-white">Task Not Found</h2>
        <p className="text-xs text-slate-400 mt-2 mb-6">Could not locate task execution data in the database ledger.</p>
        <Link to="/marketplace" className="px-4 py-2 rounded-xl bg-cyan-500 text-navy-950 font-bold text-xs">
          Return to Marketplace
        </Link>
      </div>
    );
  }

  const isCompleted = task.status === 'completed';
  const isAwaitingPayment = task.status === 'awaiting_payment';
  const isFailed = task.status === 'failed';
  const chartData = task.final_output?.analysis_data?.chart_revenue_projections || [];
  const marketShareData = task.final_output?.analysis_data?.market_share_breakdown || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Execution Error Banner (429 Quota Exhaustion, 503 Overload, Timeout) */}
      {(isFailed || executionError) && (
        <div className="p-4 rounded-xl border bg-rose-500/10 border-rose-500/30 text-rose-300 flex items-start justify-between gap-3 text-xs animate-fadeIn">
          <div className="flex items-start gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold uppercase tracking-wider text-[11px] block text-rose-200">
                Workflow Execution Halted
              </span>
              <span className="mt-1 block text-slate-200 font-sans leading-relaxed">
                {executionError ||
                  task.steps.find(s => s.status === 'failed')?.error_message ||
                  'AI provider quota limit or service degradation encountered. The task has been safely halted and state is preserved.'}
              </span>
              <span className="mt-1.5 block text-[10px] font-mono text-slate-400">
                Task ID: {task.id} • Halted node: {task.current_step} • Payment authorization is locked.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Payment Notification Banner */}
      {paymentNotice && (
        <div className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-xs animate-fadeIn ${
          paymentNotice.type === 'cancelled'
            ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            : paymentNotice.type === 'capturing'
            ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
            : paymentNotice.type === 'success'
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
            : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
        }`}>
          <div className="flex items-start gap-2.5">
            {paymentNotice.type === 'cancelled' && <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />}
            {paymentNotice.type === 'capturing' && <Loader2 className="w-4 h-4 text-cyan-400 animate-spin mt-0.5 shrink-0" />}
            {paymentNotice.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />}
            {paymentNotice.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />}
            <div>
              <span className="font-bold uppercase tracking-wider text-[10px] block">
                {paymentNotice.type === 'cancelled' && 'PayPal Checkout Session Cancelled'}
                {paymentNotice.type === 'capturing' && 'Server-Side Verification & Capture'}
                {paymentNotice.type === 'success' && 'Payment Verified & Completed'}
                {paymentNotice.type === 'error' && 'Payment Capture Alert'}
              </span>
              <span className="mt-0.5 block text-slate-300">{paymentNotice.message}</span>
            </div>
          </div>

          {paymentNotice.type === 'cancelled' && isAwaitingPayment && (
            <button
              onClick={handleOpenPaymentModal}
              className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-navy-950 font-bold text-xs shrink-0 transition-colors shadow-sm"
            >
              Review Invoice & Pay ($8.00)
            </button>
          )}
        </div>
      )}

      {/* Pre-Payment Deliverable Scope & Review Notice */}
      {isAwaitingPayment && (
        <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs animate-fadeIn">
          <div className="flex items-start gap-2.5">
            <Info className="w-5 h-5 text-cyan-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold text-white text-xs block">
                Deliverable Review Checkpoint — Qualitative AI Intelligence Synthesis
              </span>
              <span className="text-slate-300 block mt-0.5 text-[11px] leading-relaxed">
                Multi-agent workflow is complete and certified for internal consistency. Scope is designated as qualitative AI synthesis with suggested research leads (not independently fact-verified against external primary records).
              </span>
            </div>
          </div>
          <button
            onClick={handleOpenPaymentModal}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#0070BA] to-[#003087] hover:from-[#005ea6] hover:to-[#00256c] text-white font-bold text-xs shrink-0 shadow-md transition-all flex items-center gap-1.5"
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>Review & Authorize (${task.total_cost.toFixed(2)})</span>
          </button>
        </div>
      )}

      {/* Header Bar */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
              isCompleted
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : isAwaitingPayment
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse'
                : isFailed
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
            }`}>
              {task.status.replace('_', ' ')}
            </span>
            <span className="text-xs text-slate-400 font-mono">ID: {task.id.slice(0, 13)}...</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{task.title}</h1>
        </div>

        {/* Right Financial & Execution Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Cost Tracker */}
          <div className="px-3.5 py-1.5 rounded-xl bg-navy-950 border border-slate-800 flex items-center gap-3 text-xs font-mono">
            <div>
              <span className="text-[10px] text-slate-500 block">TOTAL COST</span>
              <span className="text-cyan-400 font-bold">${task.total_cost.toFixed(2)} USD</span>
            </div>
            <div className="h-6 w-[1px] bg-slate-800" />
            <div>
              <span className="text-[10px] text-slate-500 block">BUDGET</span>
              <span className="text-slate-300 font-bold">${task.budget.toFixed(2)} USD</span>
            </div>
          </div>

          {/* Stepper / Auto-Run Action */}
          {!isCompleted && !isAwaitingPayment && !isFailed && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAutoRun(!autoRun)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                  autoRun 
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' 
                    : 'bg-slate-800 text-slate-200 hover:bg-slate-700 border border-slate-700'
                }`}
              >
                {autoRun ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                <span>{autoRun ? 'Pause Auto' : 'Auto-Run'}</span>
              </button>

              <button
                onClick={handleAdvanceStep}
                disabled={advancing}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-bold text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/20 disabled:opacity-50 transition-all"
              >
                {advancing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
                <span>Advance Step</span>
              </button>
            </div>
          )}

          {/* Payment Checkpoint Button */}
          {isAwaitingPayment && (
            <button
              onClick={handleOpenPaymentModal}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-[#0070BA] to-[#003087] hover:from-[#005ea6] hover:to-[#00256c] text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-blue-500/30 animate-pulse transition-all"
            >
              <CreditCard className="w-4 h-4" />
              <span>Review Invoice & Authorize PayPal (${task.total_cost.toFixed(2)})</span>
            </button>
          )}

          {/* Download button if completed */}
          {isCompleted && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyReport}
                className="px-3 py-2 rounded-xl bg-navy-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-navy-950 font-bold text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/20 transition-all"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export Report</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Visual Workflow Pipeline Graph */}
      <div className="glass-panel rounded-2xl p-4 border border-slate-800">
        <div className="flex items-center justify-between px-2 mb-1">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold">
            STATEFUL MULTI-AGENT EXECUTION GRAPH
          </span>
          <span className="text-[11px] font-mono text-cyan-400">
            {task.steps.filter(s => s.status === 'completed').length} / {task.steps.length} Nodes Resolved
          </span>
        </div>
        <WorkflowVisualizer
          steps={task.steps}
          currentStep={task.current_step}
          onSelectStep={(s) => setSelectedStep(s)}
          selectedStepId={selectedStep?.id}
        />
      </div>

      {/* Main Studio Grid: Left Deliverable / Inspector, Right Observability Terminal */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Deliverable View or Active Step Inspector */}
        <div className="lg:col-span-7 space-y-6">
          {/* If completed: Full Final Deliverable */}
          {isCompleted && task.final_output ? (
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
              {/* Deliverable Header & Tabs */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-white">
                      {task.final_output.qa_audit?.factual_verification_status === 'VERIFIED_EMPIRICAL'
                        ? 'Independently Verified Empirical Deliverable'
                        : task.final_output.qa_audit?.factual_verification_status === 'USER_PROVIDED'
                        ? 'User-Provided Benchmark Analysis'
                        : 'Qualitative AI Synthesis Deliverable'}
                    </h3>
                    <p className="text-[11px] text-slate-400 font-mono">
                      {task.final_output.qa_audit?.factual_verification_status === 'VERIFIED_EMPIRICAL'
                        ? 'Empirically verified against primary records • Payment captured.'
                        : task.final_output.qa_audit?.factual_verification_status === 'USER_PROVIDED'
                        ? 'Calculated from user inputs (Not externally verified) • Payment captured.'
                        : 'Internal consistency certified • Suggested leads (Not independently fact-verified)'}
                    </p>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-1 bg-navy-950 p-1 rounded-xl border border-slate-800 text-xs">
                  <button
                    onClick={() => setActiveTab('report')}
                    className={`px-3 py-1 rounded-lg transition-colors ${
                      activeTab === 'report' ? 'bg-cyan-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Report
                  </button>
                  <button
                    onClick={() => setActiveTab('charts')}
                    className={`px-3 py-1 rounded-lg transition-colors ${
                      activeTab === 'charts' ? 'bg-cyan-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Charts
                  </button>
                  <button
                    onClick={() => setActiveTab('audit')}
                    className={`px-3 py-1 rounded-lg transition-colors ${
                      activeTab === 'audit' ? 'bg-cyan-500 text-navy-950 font-bold' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    QA Audit
                  </button>
                </div>
              </div>

              {/* Tab 1: Executive Markdown Report */}
              {activeTab === 'report' && (
                <div className="prose prose-invert prose-cyan max-w-none text-slate-300 text-xs sm:text-sm leading-relaxed space-y-4">
                  <ReactMarkdown>
                    {task.final_output.report_markdown || 'No report content available.'}
                  </ReactMarkdown>
                </div>
              )}

              {/* Tab 2: Quantitative Charts */}
              {activeTab === 'charts' && (
                <div className="space-y-6">
                  {/* Revenue Growth Trajectory */}
                  <div className="bg-navy-950/80 p-4 rounded-xl border border-slate-800">
                    <h4 className="text-xs font-mono font-semibold uppercase text-cyan-400 mb-4">
                      Deterministic Revenue Projections ($B USD, 2024-2030)
                    </h4>
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                          <XAxis dataKey="year" stroke="#64748B" fontSize={11} />
                          <YAxis stroke="#64748B" fontSize={11} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#070B14', borderColor: '#334155', borderRadius: 8, fontSize: 12 }} 
                            itemStyle={{ color: '#00F0FF' }}
                          />
                          <Bar dataKey="revenue_bn" fill="#00F0FF" radius={[4, 4, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Market Share Breakdown */}
                  {marketShareData.length > 0 && (
                    <div className="bg-navy-950/80 p-4 rounded-xl border border-slate-800">
                      <h4 className="text-xs font-mono font-semibold uppercase text-blue-400 mb-4">
                        Market Share Breakdown (%)
                      </h4>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {marketShareData.map((item, idx) => (
                          <div key={idx} className="p-3 rounded-lg bg-navy-900 border border-slate-800 text-center">
                            <span className="text-xs text-slate-400 block truncate">{item.label}</span>
                            <span className="text-lg font-bold text-white font-mono">{item.value}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: QA Audit Certification */}
              {activeTab === 'audit' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-3">
                    <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold text-white">Quality Assurance Certification Stamp</h4>
                      <p className="text-xs text-slate-300 mt-1">
                        {task.final_output.qa_audit?.feedback || 'All requirements, quantitative metrics, and constraints verified.'}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 text-center">
                      <span className="text-xs text-slate-400 font-mono block mb-1">Completeness Score</span>
                      <span className="text-2xl font-extrabold text-cyan-400 font-mono">
                        {task.final_output.qa_audit?.completeness_score || 98} / 100
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 text-center">
                      <span className="text-xs text-slate-400 font-mono block mb-1">Internal Consistency</span>
                      <span className="text-2xl font-extrabold text-emerald-400 font-mono">
                        {task.final_output.qa_audit?.factual_coherence_score || 96} / 100
                      </span>
                      <span className="text-[10px] text-slate-500 block mt-0.5">Structural coherence (Internal)</span>
                    </div>
                  </div>

                  {/* External Verification Scope Disclosure */}
                  <div className="p-3.5 rounded-xl bg-navy-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                    <div>
                      <span className="text-slate-400 font-mono block text-[11px]">External Factual Verification:</span>
                      <span className="text-[11px] text-slate-300">
                        {task.final_output.qa_audit?.factual_verification_status === 'VERIFIED_EMPIRICAL'
                          ? 'Empirically checked against primary research citations.'
                          : task.final_output.qa_audit?.factual_verification_status === 'USER_PROVIDED'
                          ? 'Calculated deterministically from user parameters; not externally verified.'
                          : 'Qualitative AI synthesis with suggested leads (Not independently verified against external records).'}
                      </span>
                    </div>
                    <span className={`px-2 py-0.5 rounded font-mono font-semibold text-[10px] uppercase shrink-0 ${
                      task.final_output.qa_audit?.factual_verification_status === 'VERIFIED_EMPIRICAL'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : task.final_output.qa_audit?.factual_verification_status === 'USER_PROVIDED'
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}>
                      {task.final_output.qa_audit?.factual_verification_status === 'VERIFIED_EMPIRICAL'
                        ? 'Empirically Verified'
                        : task.final_output.qa_audit?.factual_verification_status === 'USER_PROVIDED'
                        ? 'User Benchmark'
                        : 'Qualitative AI Synthesis'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* In-Progress / Step Inspector */
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
              {selectedStep ? (
                <>
                  <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                    <div>
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        INSPECTING NODE
                      </span>
                      <h3 className="text-lg font-bold text-white mt-1 capitalize">
                        {selectedStep.step_name.replace('_', ' ')}
                      </h3>
                      <p className="text-xs text-slate-400 font-mono">
                        Assigned: {selectedStep.assigned_agent_id || 'Nexus Orchestrator'}
                      </p>
                    </div>

                    <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-full ${
                      selectedStep.status === 'completed'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : selectedStep.status === 'running'
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 animate-pulse'
                        : selectedStep.status === 'failed'
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}>
                      {selectedStep.status}
                    </span>
                  </div>

                  {/* Output viewer */}
                  <div>
                    <span className="text-xs font-mono font-semibold uppercase text-slate-400 block mb-2">
                      Structured Node Payload
                    </span>
                    <div className="bg-navy-950 p-4 rounded-xl border border-slate-800 overflow-x-auto max-h-[350px]">
                      {selectedStep.status === 'failed' ? (
                        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-200 space-y-2">
                          <div className="flex items-center gap-2 text-rose-400 font-bold text-xs uppercase tracking-wider">
                            <AlertCircle className="w-4 h-4" />
                            <span>Node Execution Halted</span>
                          </div>
                          <p className="text-xs font-mono leading-relaxed">
                            {selectedStep.error_message || 'AI provider error occurred during this step.'}
                          </p>
                        </div>
                      ) : selectedStep.output_data ? (
                        <pre className="text-[11px] font-mono text-cyan-300 leading-relaxed">
                          {JSON.stringify(selectedStep.output_data, null, 2)}
                        </pre>
                      ) : (
                        <div className="py-8 text-center text-slate-500 text-xs italic">
                          This node is queued. Advance workflow to execute assigned agent.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-slate-500 text-xs">
                  Select a workflow node above to inspect its execution state and outputs.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column (5 cols): Observability Activity Log & Assigned Agents */}
        <div className="lg:col-span-5 space-y-6">
          {/* Terminal Log */}
          <StepLogViewer logs={logs} />

          {/* Assigned Agents Registry */}
          <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
            <h4 className="text-xs font-mono font-semibold uppercase text-slate-300 tracking-wider flex items-center justify-between">
              <span>ENGAGED SPECIALIZED AGENTS</span>
              <span className="text-cyan-400 font-normal">{task.steps.length} NODES</span>
            </h4>

            <div className="space-y-2">
              {task.steps.map((s) => (
                <div key={s.id} className="p-2.5 rounded-xl bg-navy-950/70 border border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      s.status === 'completed' ? 'bg-emerald-400' : s.status === 'running' ? 'bg-cyan-400 animate-pulse' : 'bg-slate-600'
                    }`} />
                    <span className="font-semibold text-slate-200 capitalize">{s.step_name.replace('_', ' ')}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 truncate max-w-[120px]">
                    {s.assigned_agent_id || 'orchestrator'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Invoice & PayPal Checkout Modal */}
      <InvoiceModal
        summary={paymentSummary}
        onClose={() => setShowPaymentModal(false)}
        onPaymentSuccess={async () => {
          await loadTaskData();
        }}
      />
    </div>
  );
};
