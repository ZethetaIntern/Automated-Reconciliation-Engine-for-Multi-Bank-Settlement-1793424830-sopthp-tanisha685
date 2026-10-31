import React, { useState } from 'react';
import { X, AlertTriangle, CheckCircle, Clock, ShieldAlert, ArrowRight, UserCheck } from 'lucide-react';

export default function ExceptionDrawer({ exception, onClose, onResolve }) {
  const [resolutionAction, setResolutionAction] = useState('MANUAL_MATCH');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!exception) return null;

  const handleResolveSubmit = async (e) => {
    e.preventDefault();
    if (!resolutionNotes.trim()) return;
    setIsSubmitting(true);
    await onResolve(exception.exception_id, {
      resolution_action: resolutionAction,
      resolution_notes: resolutionNotes,
      resolved_by: 'ops_lead_tanisha'
    });
    setIsSubmitting(false);
  };

  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL': return 'badge-critical';
      case 'HIGH': return 'badge-high';
      default: return 'badge-rule';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-in fade-in duration-100">
      <div className="w-full max-w-lg bg-[#0e131d] border-l border-[#202b3f] h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-150">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#1b2438] bg-[#090d15]">
          <div className="flex items-center gap-2.5">
            <AlertTriangle size={18} className="text-amber-400" />
            <div>
              <h3 className="font-heading font-bold text-sm text-[#f1f5f9]">Exception Details & Triage</h3>
              <div className="text-[11px] font-mono text-[#64748b]">{exception.exception_id}</div>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded text-[#64748b] hover:text-[#e2e8f0] hover:bg-[#192233]">
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5 text-xs">
          {/* Status and Category Summary */}
          <div className="p-4 rounded-lg bg-[#141b29] border border-[#1f293d] space-y-3">
            <div className="flex items-center justify-between">
              <span className={`badge-pill ${getSeverityBadge(exception.severity)}`}>
                {exception.severity} SEVERITY
              </span>
              <span className="font-mono text-[11px] text-[#94a3b8] flex items-center gap-1">
                <Clock size={12} />
                SLA: {exception.sla_minutes} mins ({exception.assigned_tier})
              </span>
            </div>

            <div>
              <div className="text-[10px] uppercase text-[#64748b] font-medium tracking-wider">Classification Category</div>
              <div className="font-mono font-bold text-sm text-[#60a5fa] mt-0.5">{exception.category}</div>
            </div>

            <div>
              <div className="text-[10px] uppercase text-[#64748b] font-medium tracking-wider">Impact Description</div>
              <div className="text-[#cbd5e1] mt-0.5 leading-relaxed">{exception.description}</div>
            </div>
          </div>

          {/* Transaction Metadata Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-[#121824] border border-[#1d273a]">
              <div className="text-[10px] text-[#64748b] uppercase">Affected Amount</div>
              <div className="font-mono font-bold text-base text-[#f8fafc] mt-1">
                ₹{parseFloat(exception.affected_amount || '0').toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-[#121824] border border-[#1d273a]">
              <div className="text-[10px] text-[#64748b] uppercase">Banking Partner</div>
              <div className="font-mono font-bold text-base text-[#38bdf8] mt-1">{exception.bank_code}</div>
            </div>
          </div>

          {/* Reference Numbers */}
          <div className="p-3 rounded-lg bg-[#121824] border border-[#1d273a] space-y-2 font-mono">
            <div>
              <span className="text-[#64748b] text-[10px]">INTERNAL RECORD ID:</span>
              <div className="text-[#e2e8f0] font-semibold">{exception.internal_txn_id || 'N/A (Missing in internal)'}</div>
            </div>
            <div className="pt-2 border-t border-[#1a2334]">
              <span className="text-[#64748b] text-[10px]">EXTERNAL STATEMENT REF:</span>
              <div className="text-[#e2e8f0] font-semibold">{exception.external_txn_id || 'N/A (Missing in statement)'}</div>
            </div>
          </div>

          {/* Suggested Resolution */}
          <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-[#93c5fd]">
            <div className="font-semibold flex items-center gap-1.5 mb-1 text-blue-300">
              <UserCheck size={14} /> Recommended Action
            </div>
            <div>{exception.suggested_resolution}</div>
          </div>

          {/* Analyst Resolution Form */}
          {exception.status === 'OPEN' || exception.status === 'ESCALATED' ? (
            <form onSubmit={handleResolveSubmit} className="p-4 rounded-lg bg-[#151c2a] border border-[#212c40] space-y-3">
              <div className="font-semibold text-[#f1f5f9] text-xs">Post Resolution Decision (Audit Enforced)</div>

              <div>
                <label className="block text-[#94a3b8] text-[10px] uppercase font-medium mb-1">Resolution Action</label>
                <select
                  value={resolutionAction}
                  onChange={(e) => setResolutionAction(e.target.value)}
                  className="w-full bg-[#101522] border border-[#26344d] rounded-md px-3 py-1.5 text-[#f1f5f9] font-mono text-xs focus:outline-none"
                >
                  <option value="MANUAL_MATCH">MANUAL_MATCH (Force-Pair Transactions)</option>
                  <option value="VOID_DUPLICATE_INTERNAL">VOID_DUPLICATE_INTERNAL (Mark Void)</option>
                  <option value="ADJUST_BANK_FEE">ADJUST_BANK_FEE (Post Ledger Charge Adjustment)</option>
                  <option value="DATE_ALIGNMENT_ACCEPTED">DATE_ALIGNMENT_ACCEPTED (Accept T+1 Variance)</option>
                  <option value="ESCALATE_COMPLIANCE">ESCALATE_COMPLIANCE (Route to AML/Risk Team)</option>
                  <option value="WRITE_OFF">WRITE_OFF (Liquidate Stale Ledger Difference)</option>
                </select>
              </div>

              <div>
                <label className="block text-[#94a3b8] text-[10px] uppercase font-medium mb-1">Mandatory Audit Justification</label>
                <textarea
                  rows={3}
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Provide detailed financial justification for statutory audit trail..."
                  className="w-full bg-[#101522] border border-[#26344d] rounded-md p-2.5 text-[#f1f5f9] text-xs focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !resolutionNotes.trim()}
                className="w-full btn-primary justify-center text-xs py-2 disabled:opacity-50"
              >
                <CheckCircle size={14} />
                <span>{isSubmitting ? 'Signing Audit Block...' : 'Submit Resolution & Sign Audit Log'}</span>
              </button>
            </form>
          ) : (
            <div className="p-4 rounded-lg bg-[#101522] border border-[#1b2438] space-y-2">
              <div className="flex items-center gap-1.5 text-[#34d399] font-semibold">
                <CheckCircle size={14} /> Resolved by {exception.resolved_by || 'SYSTEM'}
              </div>
              <div className="text-[11px] text-[#94a3b8]">Action: <span className="font-mono text-[#cbd5e1]">{exception.resolution_action}</span></div>
              <div className="text-[11px] text-[#94a3b8] italic">"{exception.resolution_notes}"</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
