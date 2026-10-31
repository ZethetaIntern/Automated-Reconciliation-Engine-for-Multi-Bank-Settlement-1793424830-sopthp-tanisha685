import React, { useState, useEffect } from 'react';
import { FileText, Download, Printer, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';

export default function ReportsView() {
  const [reportType, setReportType] = useState('daily');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchReport = async (type) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/reports/${type}`);
      const data = await res.json();
      setReportData(data);
    } catch (e) {
      console.error("Failed to fetch report", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport(reportType);
  }, [reportType]);

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadJSON = () => {
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${reportType}_reconciliation_report_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  };

  const handleDownloadCSV = () => {
    const endpoint = reportType === 'ageing' ? '/api/v1/reports/ageing/csv' : '/api/v1/reports/daily/csv';
    window.open(endpoint, '_blank');
  };

  const handleDownloadHTML = () => {
    const endpoint = reportType === 'escrow' ? '/api/v1/reports/escrow/html' : '/api/v1/reports/daily/html';
    window.open(endpoint, '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Top Selector & Export Bar */}
      <div className="inst-card p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {[
            { id: 'daily', label: 'Daily Recon Report (T+1)' },
            { id: 'ageing', label: 'Exception Ageing Matrix' },
            { id: 'escrow', label: 'RBI Clause 7.1 Escrow' },
            { id: 'audit-compliance', label: 'Statutory Audit Certificate' }
          ].map((r) => (
            <button
              key={r.id}
              onClick={() => setReportType(r.id)}
              className={`px-3 py-1.5 rounded text-xs font-semibold transition-all ${
                reportType === r.id
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-[#151c2a] text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1f283d]'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button onClick={handleDownloadHTML} className="btn-secondary text-xs" title="Official Institutional Printable HTML">
            <FileText size={13} />
            <span>Printable HTML</span>
          </button>
          <button onClick={handleDownloadCSV} className="btn-secondary text-xs" title="Download Excel Compatible CSV">
            <Download size={13} />
            <span>Export CSV</span>
          </button>
          <button onClick={handleDownloadJSON} className="btn-secondary text-xs">
            <Download size={13} />
            <span>JSON</span>
          </button>
          <button onClick={handlePrint} className="btn-primary text-xs">
            <Printer size={13} />
            <span>Print PDF</span>
          </button>
        </div>
      </div>

      {/* Structured Report Preview */}
      <div className="inst-card p-8 bg-[#0f1420] border-[#222e44] shadow-2xl font-sans print:bg-white print:text-black">
        {reportData && (
          <div className="space-y-6">
            {/* Report Header */}
            <div className="border-b border-[#1f2b40] pb-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="text-[10px] font-mono text-blue-400 font-bold uppercase tracking-wider">
                  STATUTORY COMPLIANCE DELIVERABLE
                </div>
                <h2 className="font-heading font-bold text-xl text-[#f8fafc] mt-0.5">
                  {reportData.report_title}
                </h2>
                <div className="text-xs text-[#94a3b8] mt-1">
                  {reportData.regulatory_standard || reportData.statutory_reference || reportData.regulatory_requirement}
                </div>
              </div>

              <div className="text-right font-mono text-xs text-[#64748b]">
                <div>Generated: <span className="text-[#cbd5e1]">{reportData.generated_at}</span></div>
                <div>Entity: <span className="text-blue-400 font-bold">PAYBRIDGE TECH PVT LTD</span></div>
              </div>
            </div>

            {/* Content per report type */}
            {reportType === 'daily' && reportData.summary && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-[#141b29] border border-[#1f2a3e]">
                    <div className="text-[10px] text-[#64748b] uppercase">Total Transactions</div>
                    <div className="text-xl font-bold font-mono text-[#f8fafc] mt-1">
                      {reportData.summary.total_transactions?.toLocaleString()}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-[#141b29] border border-[#1f2a3e]">
                    <div className="text-[10px] text-[#64748b] uppercase">Reconciled Match Rate</div>
                    <div className="text-xl font-bold font-mono text-[#34d399] mt-1">
                      {reportData.summary.match_rate}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-[#141b29] border border-[#1f2a3e]">
                    <div className="text-[10px] text-[#64748b] uppercase">Reconciled Volume (INR)</div>
                    <div className="text-xl font-bold font-mono text-[#60a5fa] mt-1">
                      {reportData.summary.total_reconciled_volume_inr}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-[#141b29] border border-[#1f2a3e]">
                    <div className="text-[10px] text-[#64748b] uppercase">Unresolved Variance</div>
                    <div className="text-xl font-bold font-mono text-rose-400 mt-1">
                      {reportData.summary.unreconciled_variance_inr}
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-[#131b29] border border-[#1e283b] space-y-2 text-xs font-mono">
                  <div className="flex justify-between py-1 border-b border-[#1a2334]">
                    <span className="text-[#94a3b8]">Two-Layer Balance Reconciliation:</span>
                    <span className="text-[#34d399] font-bold">{reportData.summary.balance_recon_status}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#1a2334]">
                    <span className="text-[#94a3b8]">Cryptographic SHA-256 Audit Trail:</span>
                    <span className="text-[#34d399] font-bold">{reportData.summary.audit_integrity}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-[#94a3b8]">T+1 Settlement SLA Compliance:</span>
                    <span className="text-[#34d399] font-bold">{reportData.sla_compliance?.target_t1_domestic}</span>
                  </div>
                </div>
              </div>
            )}

            {reportType === 'ageing' && reportData.ageing_buckets && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {Object.entries(reportData.ageing_buckets).map(([bucketKey, b]) => (
                    <div key={bucketKey} className="p-4 rounded-lg bg-[#131a28] border border-[#1e283b]">
                      <div className="text-[10px] uppercase font-mono text-[#94a3b8]">
                        {bucketKey.replace(/_/g, ' ')}
                      </div>
                      <div className="text-xl font-bold font-mono text-[#f8fafc] mt-1">{b.count} Items</div>
                      <div className="text-xs font-mono text-amber-400 mt-1">{b.total_amount_inr}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {reportType === 'escrow' && (
              <div className="p-5 rounded-lg bg-[#131b29] border border-[#1e283b] space-y-3 font-mono text-xs">
                <div className="flex justify-between py-1.5 border-b border-[#1a2334]">
                  <span className="text-[#94a3b8]">Total Merchant Funds Collected:</span>
                  <span className="text-[#f8fafc] font-bold">{reportData.total_collected_funds}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#1a2334]">
                  <span className="text-[#94a3b8]">Total Settled to Merchant Accounts:</span>
                  <span className="text-[#f8fafc] font-bold">{reportData.total_settled_to_merchants}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#1a2334]">
                  <span className="text-[#94a3b8]">Computed Escrow Obligation:</span>
                  <span className="text-[#60a5fa] font-bold">{reportData.computed_escrow_obligation}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#1a2334]">
                  <span className="text-[#94a3b8]">Actual Bank Escrow Account Balance:</span>
                  <span className="text-[#34d399] font-bold">{reportData.actual_bank_escrow_balance}</span>
                </div>
                <div className="flex justify-between py-1.5 pt-3">
                  <span className="text-[#f8fafc] font-bold">RBI Clause 7.1 Compliance Status:</span>
                  <span className="text-[#34d399] font-bold text-sm">{reportData.compliance_status}</span>
                </div>
              </div>
            )}

            {reportType === 'audit-compliance' && (
              <div className="p-5 rounded-lg bg-[#131b29] border border-[#1e283b] space-y-3 font-mono text-xs">
                <div className="flex items-center gap-2 text-[#34d399] font-bold text-sm pb-2 border-b border-[#1a2334]">
                  <ShieldCheck size={18} />
                  STATUS: {reportData.audit_chain_status}
                </div>
                <div>Hash Algorithm: <span className="text-[#cbd5e1]">{reportData.hash_algorithm}</span></div>
                <div>Total Blocks Verified: <span className="text-[#cbd5e1]">{reportData.total_audit_events_verified}</span></div>
                <div>Latest Hash Anchor: <span className="text-[#60a5fa]">{reportData.latest_block_hash}</span></div>
                <div>Violations / Tampering Detected: <span className="text-[#34d399] font-bold">{reportData.tamper_violations_count}</span></div>
                <div>Storage Mandate: <span className="text-[#cbd5e1]">{reportData.retention_policy_compliance}</span></div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
