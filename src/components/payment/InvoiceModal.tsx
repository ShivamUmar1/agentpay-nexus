import React, { useState } from 'react';
import { 
  X, 
  ShieldCheck, 
  CreditCard, 
  AlertTriangle, 
  CheckCircle2, 
  DollarSign, 
  ExternalLink,
  Lock,
  Loader2
} from 'lucide-react';
import { PaymentSummary } from '../../types';
import { api } from '../../services/api';

interface InvoiceModalProps {
  summary: PaymentSummary | null;
  onClose: () => void;
  onPaymentSuccess: (result: any) => void;
}

export const InvoiceModal: React.FC<InvoiceModalProps> = ({
  summary,
  onClose,
  onPaymentSuccess
}) => {
  const [loading, setLoading] = useState(false);
  const [redirecting, setRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!summary) return null;

  const handleAuthorizePayPal = async () => {
    try {
      setLoading(true);
      setError(null);

      // Explicit return and cancel URLs
      const returnUrl = `${window.location.origin}/tasks/${summary.task_id}?approved=true`;
      const cancelUrl = `${window.location.origin}/tasks/${summary.task_id}?cancelled=true`;

      // Step 1: Create or retrieve active PayPal order via backend
      const order = await api.createPayPalOrder(summary.task_id, returnUrl, cancelUrl);

      // Step 2: If official approval URL is present, redirect buyer to PayPal Sandbox
      if (order.approval_url) {
        setRedirecting(true);
        window.location.href = order.approval_url;
        return;
      }

      // Step 3: Fallback for simulated demo mode only
      const capture = await api.capturePayPalOrder(summary.task_id, order.order_id);
      if (capture.success) {
        onPaymentSuccess(capture);
        onClose();
      } else {
        setError(capture.message || 'Payment capture failed.');
      }
    } catch (err: any) {
      setError(err.message || 'Payment processing error.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-xl rounded-2xl bg-navy-900 border border-slate-700/80 shadow-2xl p-6 text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                OFFICIAL INVOICE
              </span>
              <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" />
                Ledger Verified
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">Marketplace Settlement Authorization</h2>
            <p className="text-xs text-slate-400 mt-0.5">Task: {summary.task_title}</p>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Budget Warning if Exceeded */}
        {summary.is_budget_exceeded && (
          <div className="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-300">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <div>
              <span className="font-semibold block">Budget Threshold Alert</span>
              <span>
                Calculated service fee (${summary.total_amount.toFixed(2)}) exceeds specified maximum budget (${summary.budget.toFixed(2)}). User authorization required to proceed.
              </span>
            </div>
          </div>
        )}

        {/* Itemized Line Items Table */}
        <div className="mt-5 space-y-3">
          <span className="text-xs font-mono font-semibold uppercase text-slate-400 block tracking-wider">
            Itemized Agent Service Fees
          </span>

          <div className="rounded-xl border border-slate-800 bg-navy-950/60 divide-y divide-slate-800/80 overflow-hidden">
            {summary.items.map((item, idx) => (
              <div key={idx} className="p-3 flex items-center justify-between text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white">{item.agent_name}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                      {item.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{item.description}</p>
                </div>
                <span className="font-mono font-bold text-slate-200">
                  ${item.total.toFixed(2)} {summary.currency}
                </span>
              </div>
            ))}
          </div>

          {/* Totals */}
          <div className="p-4 rounded-xl bg-navy-950 border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Marketplace Subtotal</span>
              <span className="font-mono">${summary.subtotal.toFixed(2)} USD</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Platform Service Surcharge</span>
              <span className="font-mono text-emerald-400">$0.00 (Waived)</span>
            </div>
            <div className="pt-2 border-t border-slate-800 flex justify-between text-sm font-bold text-white">
              <span className="flex items-center gap-1.5">
                <Lock className="w-4 h-4 text-cyan-400" />
                Total Authorized Amount
              </span>
              <span className="font-mono text-lg text-cyan-400">
                ${summary.total_amount.toFixed(2)} {summary.currency}
              </span>
            </div>
          </div>
        </div>

        {/* Error message if any */}
        {error && (
          <div className="mt-3 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {/* PayPal Checkout Actions */}
        <div className="mt-6 space-y-3">
          <button
            onClick={handleAuthorizePayPal}
            disabled={loading || redirecting}
            className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-[#0070BA] to-[#003087] hover:from-[#005ea6] hover:to-[#00256c] text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 transition-all duration-200 disabled:opacity-50"
          >
            {redirecting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Redirecting to PayPal Checkout...</span>
              </>
            ) : loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Contacting PayPal Orders v2...</span>
              </>
            ) : (
              <>
                <CreditCard className="w-4 h-4" />
                <span>Authorize & Pay with PayPal Checkout (${summary.total_amount.toFixed(2)})</span>
              </>
            )}
          </button>

          <p className="text-center text-[11px] text-slate-500">
            Protected by PayPal Buyer Protection & Server-Side Verification. Deliverables unlock instantly upon capture.
          </p>
        </div>
      </div>
    </div>
  );
};
