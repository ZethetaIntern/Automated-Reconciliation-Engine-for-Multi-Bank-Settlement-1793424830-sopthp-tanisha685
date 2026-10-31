import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, Lock, RefreshCw, Key, ArrowDown, Search } from 'lucide-react';

export default function AuditView() {
  const [auditEntries, setAuditEntries] = useState([]);
  const [verificationResult, setVerificationResult] = useState(null);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const fetchAuditLog = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/audit?limit=50');
      const data = await res.json();
      setAuditEntries(data.entries || []);
    } catch (e) {
      console.error("Failed to load audit log", e);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const res = await fetch('/api/v1/audit/verify');
      const data = await res.json();
      setVerificationResult(data);
    } catch (e) {
      console.error("Verification error", e);
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchAuditLog();
    handleVerifyChain();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner: Verification Status */}
      <div className="inst-card p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-heading font-bold text-base text-[#f8fafc]">
                Cryptographic Immutable Audit Trail
              </h3>
              <span className="badge-pill badge-exact text-[10px]">SHA-256 Chained</span>
            </div>
            <div className="text-xs text-[#94a3b8] mt-1">
              Sec. 128 Companies Act (2013) & RBI Cyber Security Append-Only Ledger
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="btn-primary text-xs"
          >
            <ShieldCheck size={14} className={verifying ? 'animate-spin' : ''} />
            <span>{verifying ? 'Recalculating Hashes...' : 'Verify Cryptographic Integrity'}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Block Chain Stream & JSON Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Block Stream */}
        <div className="lg:col-span-2 inst-card p-5 space-y-4">
          <div className="flex items-center justify-between text-xs text-[#94a3b8] border-b border-[#1b2538] pb-3">
            <span>Audit Block Ledger ({auditEntries.length} Recorded Events)</span>
            <span className="font-mono">Merkle-Chained Blocks</span>
          </div>

          <div className="space-y-3">
            {auditEntries.map((entry, idx) => (
              <div
                key={entry.event_id}
                onClick={() => setSelectedEntry(entry)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer font-mono text-xs ${
                  selectedEntry?.event_id === entry.event_id
                    ? 'bg-[#182338] border-blue-500/50 shadow-md'
                    : 'bg-[#121826] border-[#1d273a] hover:border-[#2a3854]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold text-[11px]">
                      {entry.action_type}
                    </span>
                    <span className="text-[#94a3b8] text-[11px]">{entry.actor}</span>
                  </div>
                  <span className="text-[10px] text-[#64748b]">
                    {new Date(entry.timestamp).toISOString()}
                  </span>
                </div>

                <div className="text-[#cbd5e1] text-xs font-sans mb-2 font-medium">
                  {entry.rationale}
                </div>

                <div className="pt-2 border-t border-[#182233] space-y-1 text-[10px] text-[#64748b]">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="text-[#475569]">PREV_HASH:</span>
                    <span className="text-[#94a3b8]">{entry.prev_hash}</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="text-[#34d399] font-bold">BLOCK_HASH:</span>
                    <span className="text-[#34d399]">{entry.sha256_hash}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* State Diff Inspector */}
        <div className="inst-card p-5">
          <h3 className="font-heading font-bold text-sm text-[#f1f5f9] mb-1">
            Audit State Diff Inspector
          </h3>
          <div className="text-[11px] text-[#64748b] mb-4">
            Before vs After state representation for statutory audit
          </div>

          {selectedEntry ? (
            <div className="space-y-4 text-xs font-mono">
              <div className="p-3 rounded-lg bg-[#141d2d] border border-[#202d44] space-y-1.5">
                <div><span className="text-[#64748b]">Event ID:</span> <span className="text-blue-400">{selectedEntry.event_id}</span></div>
                <div><span className="text-[#64748b]">Action:</span> <span className="text-[#e2e8f0]">{selectedEntry.action_type}</span></div>
                <div><span className="text-[#64748b]">Actor:</span> <span className="text-[#38bdf8]">{selectedEntry.actor}</span></div>
              </div>

              <div>
                <div className="text-[10px] uppercase text-[#64748b] font-semibold mb-1">Before State:</div>
                <pre className="p-2.5 rounded-lg bg-[#0b0f17] border border-[#1a2334] text-[11px] text-[#94a3b8] overflow-x-auto max-h-36">
                  {JSON.stringify(selectedEntry.before_state || {}, null, 2)}
                </pre>
              </div>

              <div>
                <div className="text-[10px] uppercase text-[#64748b] font-semibold mb-1">After State:</div>
                <pre className="p-2.5 rounded-lg bg-[#0b0f17] border border-[#1a2334] text-[11px] text-[#34d399] overflow-x-auto max-h-36">
                  {JSON.stringify(selectedEntry.after_state || {}, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-[#64748b] text-xs">
              Click any block in the audit trail to inspect full before/after cryptographic diffs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
