import React from 'react';
import { 
  CheckCircle2, 
  Clock, 
  Loader2, 
  AlertCircle, 
  Cpu, 
  Search, 
  BarChart3, 
  FileText, 
  ShieldCheck, 
  DollarSign, 
  CreditCard, 
  Award,
  ChevronRight
} from 'lucide-react';
import { TaskStep } from '../../types';

interface WorkflowVisualizerProps {
  steps: TaskStep[];
  currentStep: string;
  onSelectStep: (step: TaskStep) => void;
  selectedStepId?: string;
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  planning: <Cpu className="w-4 h-4" />,
  research: <Search className="w-4 h-4" />,
  data_analysis: <BarChart3 className="w-4 h-4" />,
  content_generation: <FileText className="w-4 h-4" />,
  quality_assurance: <ShieldCheck className="w-4 h-4" />,
  finance_calculation: <DollarSign className="w-4 h-4" />,
  payment_approval: <CreditCard className="w-4 h-4" />,
  final_delivery: <Award className="w-4 h-4" />
};

const STEP_TITLES: Record<string, string> = {
  planning: 'Orchestrator',
  research: 'Deep Research',
  data_analysis: 'Quant Analytics',
  content_generation: 'Content Synthesis',
  quality_assurance: 'Fact Auditor',
  finance_calculation: 'Ledger Finance',
  payment_approval: 'PayPal Checkout',
  final_delivery: 'Final Delivery'
};

export const WorkflowVisualizer: React.FC<WorkflowVisualizerProps> = ({
  steps,
  currentStep,
  onSelectStep,
  selectedStepId
}) => {
  return (
    <div className="w-full overflow-x-auto py-4 px-2">
      <div className="flex items-center justify-between min-w-[850px] gap-2">
        {steps.map((step, index) => {
          const isCompleted = step.status === 'completed';
          const isRunning = step.status === 'running' || currentStep === step.step_name;
          const isFailed = step.status === 'failed';
          const isSelected = selectedStepId === step.id;

          return (
            <React.Fragment key={step.id}>
              {/* Node Card */}
              <button
                onClick={() => onSelectStep(step)}
                className={`flex-1 flex flex-col items-center p-3 rounded-xl transition-all duration-300 relative border ${
                  isSelected
                    ? 'bg-navy-800 border-cyan-400 shadow-lg shadow-cyan-500/20 scale-105'
                    : isRunning
                    ? 'bg-navy-850 border-cyan-500/60 shadow-md shadow-cyan-500/10 animate-pulse'
                    : isCompleted
                    ? 'bg-navy-900/90 border-emerald-500/30 hover:border-emerald-500/60'
                    : 'bg-navy-950/60 border-slate-800 hover:border-slate-700 opacity-70'
                }`}
              >
                {/* Node Status Badge */}
                <div className="mb-2">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-colors ${
                    isCompleted
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/40'
                      : isRunning
                      ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500 animate-spin-slow'
                      : isFailed
                      ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                      : 'bg-slate-800 text-slate-500 border border-slate-700'
                  }`}>
                    {isRunning ? (
                      <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                    ) : (
                      STEP_ICONS[step.step_name] || <Clock className="w-4 h-4" />
                    )}
                  </div>
                </div>

                {/* Node Name */}
                <span className={`text-[11px] font-bold tracking-tight text-center truncate max-w-full ${
                  isSelected ? 'text-cyan-300' : isCompleted ? 'text-slate-100' : 'text-slate-400'
                }`}>
                  {STEP_TITLES[step.step_name] || step.step_name}
                </span>

                {/* Status Indicator */}
                <div className="flex items-center gap-1 mt-1">
                  {isCompleted && (
                    <span className="flex items-center gap-0.5 text-[9px] font-mono text-emerald-400">
                      <CheckCircle2 className="w-2.5 h-2.5" />
                      Done
                    </span>
                  )}
                  {isRunning && (
                    <span className="text-[9px] font-mono text-cyan-400 animate-pulse">
                      Active
                    </span>
                  )}
                  {!isCompleted && !isRunning && !isFailed && (
                    <span className="text-[9px] font-mono text-slate-500">
                      Queued
                    </span>
                  )}
                  {isFailed && (
                    <span className="text-[9px] font-mono text-rose-400">
                      Error
                    </span>
                  )}
                </div>
              </button>

              {/* Connecting arrow */}
              {index < steps.length - 1 && (
                <div className="shrink-0 flex items-center px-1">
                  <ChevronRight className={`w-4 h-4 ${
                    isCompleted ? 'text-emerald-500/60' : 'text-slate-700'
                  }`} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
