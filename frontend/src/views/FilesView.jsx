import React, { useState, useEffect } from 'react';
import { Database, Upload, FileCode, CheckCircle, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';

export default function FilesView() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [selectedBank, setSelectedBank] = useState('HDFC');
  const [selectedFileObj, setSelectedFileObj] = useState(null);

  const fetchFiles = async () => {
    try {
      const res = await fetch('/api/v1/files');
      const data = await res.json();
      setFiles(data || []);
    } catch (e) {
      console.error("Failed to fetch files", e);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!selectedFileObj) return;

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', selectedFileObj);
    formData.append('bank_code', selectedBank);

    try {
      const res = await fetch('/api/v1/files/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        setUploadResult({ error: data.detail || 'File upload failed' });
      } else {
        setUploadResult({ success: true, data: data.file_details });
        fetchFiles();
      }
    } catch (err) {
      setUploadResult({ error: err.message });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Box & Config Management */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card */}
        <div className="inst-card p-5">
          <div className="flex items-center gap-2 mb-1">
            <Upload size={16} className="text-blue-400" />
            <h3 className="font-heading font-bold text-sm text-[#f1f5f9]">Ingest Bank Statement File</h3>
          </div>
          <div className="text-[11px] text-[#64748b] mb-4">
            Supports CSV, SWIFT MT940 (.sta), ISO 20022 CAMT.053 (.xml)
          </div>

          <form onSubmit={handleFileUpload} className="space-y-4 text-xs">
            <div>
              <label className="block text-[#94a3b8] uppercase text-[10px] font-medium mb-1">Bank Partner</label>
              <select
                value={selectedBank}
                onChange={(e) => setSelectedBank(e.target.value)}
                className="w-full bg-[#121824] border border-[#202c3f] rounded-lg px-3 py-1.5 text-[#f1f5f9] font-mono focus:outline-none"
              >
                <option value="HDFC">HDFC Bank (Standard CSV)</option>
                <option value="ICICI">ICICI Bank (Variant CSV)</option>
                <option value="AXIS">Axis Bank (SWIFT MT940 Period Decimals)</option>
                <option value="SBI">SBI (SWIFT MT940 Missing Funds Code)</option>
                <option value="KOTAK">Kotak Mahindra Bank (CAMT.053 XML)</option>
                <option value="YESBANK">Yes Bank (CSV)</option>
                <option value="INDUSIND">IndusInd Bank (CSV)</option>
              </select>
            </div>

            <div>
              <label className="block text-[#94a3b8] uppercase text-[10px] font-medium mb-1">Select Statement File</label>
              <input
                type="file"
                onChange={(e) => setSelectedFileObj(e.target.files[0])}
                className="w-full bg-[#121824] border border-[#202c3f] rounded-lg p-2 text-xs text-[#cbd5e1] file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:bg-blue-600 file:text-white"
              />
            </div>

            <button
              type="submit"
              disabled={uploading || !selectedFileObj}
              className="w-full btn-primary justify-center text-xs py-2 disabled:opacity-50"
            >
              <Upload size={14} />
              <span>{uploading ? 'Parsing & Hashing...' : 'Ingest & Compute SHA-256'}</span>
            </button>
          </form>

          {uploadResult?.success && (
            <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs">
              <div className="font-bold flex items-center gap-1"><CheckCircle size={13} /> Ingestion Verified</div>
              <div className="text-[11px] font-mono text-[#cbd5e1] mt-1">
                Parsed {uploadResult.data.record_count} records. SHA-256 hash verified.
              </div>
            </div>
          )}

          {uploadResult?.error && (
            <div className="mt-3 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
              <div className="font-bold flex items-center gap-1"><AlertCircle size={13} /> Ingestion Rejected</div>
              <div className="text-[11px] mt-1 text-rose-200">{uploadResult.error}</div>
            </div>
          )}
        </div>

        {/* Bank Config Specification (Scenario B4.1) */}
        <div className="lg:col-span-2 inst-card p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <FileCode size={16} className="text-amber-400" />
              <h3 className="font-heading font-bold text-sm text-[#f1f5f9]">Hot-Swappable Bank YAML Mappings</h3>
            </div>
            <span className="text-[10px] font-mono text-[#64748b]">Scenario B4.1 Protection</span>
          </div>
          <div className="text-[11px] text-[#64748b] mb-3">
            Adaptive parser mapping without downtime restart
          </div>

          <div className="p-3 rounded-lg bg-[#0b0f17] border border-[#1a2334] font-mono text-xs text-[#cbd5e1] overflow-x-auto max-h-56">
            <pre>{`bank_code: "ICICI"
bank_name: "ICICI Bank Limited"
supported_formats: ["CSV", "MT940"]
timezone: "Asia/Kolkata"
settlement_cycle: "T+1"
reconciliation_window_days: 5
currency: "INR"
column_mappings:
  txn_id: "urn_ref"
  txn_date: "value_date"
  amount: "settlement_value"
  currency: "txn_currency"
  direction: "txn_indicator"
  counterparty_name: "payee_name"
  counterparty_account: "payee_account"
  bank_ref: "icici_ref_number"
  narration: "description"
  settlement_date: "posting_date"`}</pre>
          </div>
        </div>
      </div>

      {/* Ingested Files Registry */}
      <div className="inst-card p-5">
        <h3 className="font-heading font-bold text-sm text-[#f1f5f9] mb-1">
          Ingested File Registry & SHA-256 Checksums
        </h3>
        <div className="text-[11px] text-[#64748b] mb-4">
          Tamper verification and duplicate settlement protection (Scenario B4.4)
        </div>

        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>File ID</th>
                <th>File Name</th>
                <th>Bank</th>
                <th>Format</th>
                <th>Records</th>
                <th>SHA-256 Fingerprint</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.file_id}>
                  <td className="font-mono text-[11px] text-blue-400 font-semibold">{f.file_id}</td>
                  <td className="font-mono text-xs font-semibold text-[#f8fafc]">{f.filename}</td>
                  <td className="font-mono text-xs text-[#38bdf8]">{f.bank_code}</td>
                  <td className="font-mono text-xs text-[#94a3b8]">{f.format}</td>
                  <td className="font-mono text-xs font-bold text-[#e2e8f0]">{(f.record_count || 0).toLocaleString()}</td>
                  <td className="font-mono text-[11px] text-[#64748b] truncate max-w-xs">{f.sha256_hash}</td>
                  <td>
                    <span className="badge-pill badge-exact text-[10px]">
                      {f.status}
                    </span>
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
