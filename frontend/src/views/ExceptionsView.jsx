import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, CheckCircle, Clock, ShieldAlert, 
  Filter, Search, ArrowRight, RefreshCw, Zap, UserCheck
} from 'lucide-react';

export default function ExceptionsView({ onSelectException }) {
  const [exceptions, setExceptions] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchExceptions = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/exceptions?limit=150');
      const data = await res.json();
      setExceptions(data.exceptions || []);
    } catch (e) {
      console.error("Failed to fetch exceptions", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExceptions();
  }, []);

  const categories = [
    'ALL',
    'DIRECTION_REVERSAL',
    'AMOUNT_MISMATCH',
    'DUPLICATE_INTERNAL',
    'DUPLICATE_EXTERNAL',
    'DATE_MISMATCH',
    'CURRENCY_MISMATCH',
    'FEE_DEDUCTION',
    'FX_VARIANCE',
    'MISSING_INTERNAL',
    'MISSING_EXTERNAL',
    'PARTIAL_MATCH',
    'NETTED_SETTLEMENT',
    'STALE_TRANSACTION',
    'FORMAT_ERROR',
    'REFERENCE_TRUNCATED',
    'TIMEZONE_OFFSET',
    'REVERSAL_PENDING',
    'REGULATORY_HOLD'
  ];

  const filteredExceptions = exceptions.filter((exc) => {
    if (selectedCategory !== 'ALL' && exc.category !== selectedCategory) return false;
    if (selectedSeverity !== 'ALL' && exc.severity !== selectedSeverity) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const id = (exc.exception_id || '').toLowerCase();
      const inId = (exc.internal_txn_id || '').toLowerCase();
      const extId = (exc.external_txn_id || '').toLowerCase();
      const desc = (exc.description || '').toLowerCase();
      if (!id.includes(q) && !inId.includes(q) && !extId.includes(q) && !desc.includes(q)) return false;
    }
    return true;
  });

  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL': return 'badge-critical';
      case 'HIGH': return 'badge-high';
      default: return 'badge-rule';
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Controls & Category Filters */}
      <div className="inst-card p-4 space-y-3">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-400" />
            <div>
              <h3 className="font-heading font-bold text-sm text-[#f1f5f9]">18-Category Exception Triage Queue</h3>
              <div className="text-[11px] text-[#64748b]">Tiered SLA escalation per RBI Master Direction</div>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative w-full md:w-64">
              <Search size={14} className="absolute left-3 top-2.5 text-[#64748b]" />
              <input
                type="text"
                placeholder="Search exception ID, ref, or memo..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#141b29] border border-[#212c3f] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[#f1f5f9] focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
            <button 
              onClick={fetchExceptions} 
              className="btn-secondary text-xs"
              title="Refresh exception queue"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Category Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] font-mono">
          {categories.map((c) => (
            <button
              key={c}
              onClick={() => setSelectedCategory(c)}
              className={`px-2.5 py-1 rounded whitespace-nowrap transition-all ${
                selectedCategory === c
                  ? 'bg-blue-600 text-white font-bold shadow-sm'
                  : 'bg-[#151c2a] text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1e273a]'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Exception Table */}
      <div className="inst-card p-4">
        <div className="flex items-center justify-between mb-3 text-xs text-[#94a3b8]">
          <span>Displaying {filteredExceptions.length} active exceptions</span>
          <span className="font-mono text-rose-400">Direction Reversal SLA: 30 mins (Tier 4 Compliance)</span>
        </div>

        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Exception ID</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Affected Amount</th>
                <th>Bank</th>
                <th>SLA Countdown</th>
                <th>Tier</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredExceptions.map((exc) => (
                <tr 
                  key={exc.exception_id}
                  className="cursor-pointer hover:bg-[#182233]"
                  onClick={() => onSelectException(exc)}
                >
                  <td className="font-mono text-[11px] text-blue-400 font-semibold">{exc.exception_id}</td>
                  <td className="font-mono text-[11px] text-[#e2e8f0] font-medium">{exc.category}</td>
                  <td>
                    <span className={`badge-pill ${getSeverityBadge(exc.severity)}`}>
                      {exc.severity}
                    </span>
                  </td>
                  <td className="font-mono font-bold text-[#f8fafc]">
                    ₹{parseFloat(exc.affected_amount || '0').toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="font-mono text-[#38bdf8] font-semibold">{exc.bank_code}</td>
                  <td className="font-mono text-xs">
                    <span className={`flex items-center gap-1 ${exc.is_sla_breached ? 'text-rose-400 font-bold' : 'text-[#cbd5e1]'}`}>
                      <Clock size={12} className={exc.is_sla_breached ? 'text-rose-400' : 'text-[#64748b]'} />
                      {exc.sla_minutes}m SLA
                    </span>
                  </td>
                  <td className="font-mono text-[11px] text-[#94a3b8]">{exc.assigned_tier}</td>
                  <td>
                    <span className={`badge-pill ${exc.status === 'RESOLVED' || exc.status === 'AUTO_RESOLVED' ? 'badge-exact' : 'badge-rule'}`}>
                      {exc.status}
                    </span>
                  </td>
                  <td>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectException(exc);
                      }}
                      className="btn-secondary text-[11px] py-1 px-2"
                    >
                      Triage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
