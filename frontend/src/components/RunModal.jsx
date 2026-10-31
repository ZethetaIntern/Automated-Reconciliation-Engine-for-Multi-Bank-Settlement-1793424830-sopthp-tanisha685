import React, { useState } from 'react';
import { X, Play, Sliders, Zap, Shield, HelpCircle } from 'lucide-react';

export default function RunModal({ isOpen, onClose, onExecute, isRunning }) {
  const [bankCode, setBankCode] = useState('ALL');
  const [fastMode, setFastMode] = useState(false);
  const [toleranceAmount, setToleranceAmount] = useState('0.01');
  const [toleranceFx, setToleranceFx] = useState('0.015');
  const [dateOffsetDays, setDateOffsetDays] = useState(1);

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onExecute({
      bank_code: bankCode,
      fast_mode: fastMode,
      tolerance_amount: parseFloat(toleranceAmount),
      tolerance_fx: parseFloat(toleranceFx),
      date_offset_days: parseInt(dateOffsetDays, 10)
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#101522] border border-[#232f46] rounded-xl w-full max-w-md overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1b2538] bg-[#0c101b]">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-[#38bdf8]" />
            <h3 className="font-heading font-bold text-sm text-[#f1f5f9]">Execute Reconciliation Run</h3>
          </div>
          <button onClick={onClose} className="text-[#64748b] hover:text-[#e2e8f0]">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {/* Bank Target */}
          <div>
            <label className="block text-[#94a3b8] font-medium mb-1.5 uppercase tracking-wider text-[10px]">
              Banking Partner Target
            </label>
            <select
              value={bankCode}
              onChange={(e) => setBankCode(e.target.value)}
              className="w-full bg-[#161f30] border border-[#25344f] rounded-lg px-3 py-2 text-[#f1f5f9] focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="ALL">ALL 7 PARTNERS (Aggregated Production Run)</option>
              <option value="HDFC">HDFC Bank (CSV Format)</option>
              <option value="ICICI">ICICI Bank (CSV Variant)</option>
              <option value="AXIS">Axis Bank (SWIFT MT940)</option>
              <option value="SBI">State Bank of India (SWIFT MT940)</option>
              <option value="KOTAK">Kotak Mahindra Bank (ISO 20022 CAMT.053)</option>
              <option value="YESBANK">Yes Bank (CSV)</option>
              <option value="INDUSIND">IndusInd Bank (CSV)</option>
            </select>
          </div>

          {/* Mode Switch: Fast Mode (Exact Only for Backlog Clearance) */}
          <div className="p-3 rounded-lg bg-[#141d2e] border border-[#202d44] flex items-start gap-3">
            <input
              type="checkbox"
              id="fastMode"
              checked={fastMode}
              onChange={(e) => setFastMode(e.target.checked)}
              className="mt-0.5 rounded bg-[#1e293b] border-slate-600 text-blue-600 focus:ring-0"
            />
            <label htmlFor="fastMode" className="cursor-pointer">
              <div className="font-semibold text-[#f1f5f9] flex items-center gap-1.5">
                Fast Mode (Emergency Backlog Clearance)
              </div>
              <div className="text-[11px] text-[#94a3b8] mt-0.5">
                Runs Stage 1 exact hash-matching only. Skips fuzzy & rule-based subset search for rapid T+1 interim reporting (Scenario B4.3).
              </div>
            </label>
          </div>

          {/* Tolerances */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[#94a3b8] font-medium mb-1 text-[10px] uppercase">
                Amount Tolerance (INR)
              </label>
              <input
                type="text"
                value={toleranceAmount}
                onChange={(e) => setToleranceAmount(e.target.value)}
                className="w-full bg-[#161f30] border border-[#25344f] rounded-lg px-3 py-1.5 text-[#f1f5f9] font-mono"
              />
            </div>
            <div>
              <label className="block text-[#94a3b8] font-medium mb-1 text-[10px] uppercase">
                FX Tolerance Band
              </label>
              <input
                type="text"
                value={toleranceFx}
                onChange={(e) => setToleranceFx(e.target.value)}
                className="w-full bg-[#161f30] border border-[#25344f] rounded-lg px-3 py-1.5 text-[#f1f5f9] font-mono"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-[#1b2538] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isRunning}
              className="btn-primary"
            >
              <Play size={14} className="fill-white" />
              <span>{isRunning ? 'Running Pipeline...' : 'Start Execution'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
