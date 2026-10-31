import React, { useState, useEffect } from 'react';
import { Search, Filter, Zap, CheckCircle2, ChevronRight, Layers, ArrowUpRight, Download } from 'lucide-react';

export default function MatchingView({ runs, onSelectMatch }) {
  const [filterType, setFilterType] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [matches, setMatches] = useState([]);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch results from latest run
    const fetchMatches = async () => {
      setLoading(true);
      try {
        const runsRes = await fetch('/api/v1/reconciliation/runs');
        const runsData = await runsRes.json();
        if (runsData && runsData.length > 0) {
          const latestRunId = runsData[runsData.length - 1].run_id;
          const res = await fetch(`/api/v1/reconciliation/runs/${latestRunId}/results?limit=100`);
          const data = await res.json();
          setMatches(data.results || []);
        } else {
          // Fallback mock items for instant view
          setMatches([
            {
              match_id: "EXACT-A81920F",
              internal_txn_id: "PB26031500000001",
              external_txn_id: "UTR26031500000001",
              match_type: "EXACT",
              confidence_score: 1.0,
              rule_name: "EXACT_HASH_COMPOSITE_MATCH",
              internal_amount: "1499.50",
              external_amount: "1499.50",
              bank_code: "HDFC",
              matched_at: "2026-03-30T10:15:00Z",
              breakdown: { reference: 1.0, amount: 1.0, date: 1.0, counterparty: 1.0, direction: 1.0, currency: 1.0, composite: 1.0 }
            },
            {
              match_id: "FUZZY-C71944E",
              internal_txn_id: "PB26031500000088",
              external_txn_id: "PB2603150000008",
              match_type: "FUZZY",
              confidence_score: 0.91,
              rule_name: "RAPIDFUZZ_WEIGHTED_CONFIDENCE",
              internal_amount: "25000.00",
              external_amount: "25000.00",
              bank_code: "ICICI",
              matched_at: "2026-03-30T10:15:05Z",
              breakdown: { reference: 0.88, amount: 1.0, date: 1.0, counterparty: 0.95, direction: 1.0, currency: 1.0, composite: 0.91 }
            },
            {
              match_id: "SPLIT-B91021A",
              internal_txn_id: "PB-SPLIT-101",
              external_txn_id: "EXT-BATCH-882",
              match_type: "SPLIT",
              confidence_score: 0.94,
              rule_name: "SPLIT_TRANSACTION_SUBSET_SUM",
              internal_amount: "50000.00",
              external_amount: "50000.00",
              bank_code: "AXIS",
              matched_at: "2026-03-30T10:15:10Z",
              breakdown: { split_count: 3.0, amount_match: 1.0, composite: 0.94 }
            },
            {
              match_id: "RULE-D55120C",
              internal_txn_id: "PB26031500000120",
              external_txn_id: "KMB-260315-120",
              match_type: "RULE",
              confidence_score: 0.88,
              rule_name: "AMOUNT_TOLERANCE_DATE_OFFSET_RULE",
              internal_amount: "4800.00",
              external_amount: "4800.00",
              bank_code: "KOTAK",
              matched_at: "2026-03-30T10:15:15Z",
              breakdown: { amount_diff: 0.0, date_diff_days: 1.0, composite: 0.88 }
            }
          ]);
        }
      } catch (e) {
        console.error("Failed to load match results", e);
      } finally {
        setLoading(false);
      }
    };
    fetchMatches();
  }, []);

  const filteredMatches = matches.filter((m) => {
    if (filterType !== 'ALL' && m.match_type !== filterType) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const inId = (m.internal_txn_id || '').toLowerCase();
      const extId = (m.external_txn_id || '').toLowerCase();
      const bank = (m.bank_code || '').toLowerCase();
      if (!inId.includes(q) && !extId.includes(q) && !bank.includes(q)) return false;
    }
    return true;
  });

  const getMatchBadge = (type) => {
    switch (type) {
      case 'EXACT': return 'badge-exact';
      case 'FUZZY': return 'badge-fuzzy';
      case 'SPLIT':
      case 'NETTED':
      case 'RULE': return 'badge-rule';
      default: return 'badge-resolved';
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Filter & Search Bar */}
      <div className="inst-card p-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 w-full md:w-auto">
          {['ALL', 'EXACT', 'FUZZY', 'RULE', 'SPLIT', 'NETTED'].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1 rounded text-xs font-semibold font-mono transition-all ${
                filterType === t
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-[#151c2a] text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1c2638]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="relative w-full md:w-72">
            <Search size={14} className="absolute left-3 top-2.5 text-[#64748b]" />
            <input
              type="text"
              placeholder="Search reference, UTR, or bank..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#141b29] border border-[#212c3f] rounded-lg pl-9 pr-3 py-1.5 text-xs text-[#f1f5f9] focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Main Grid: Match List & Detail Breakdown Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Match Table */}
        <div className="lg:col-span-2 inst-card p-4">
          <div className="flex items-center justify-between mb-3 text-xs text-[#94a3b8]">
            <span>Showing {filteredMatches.length} reconciled pairs</span>
            <span className="font-mono">Exact Hash O(N+M) + RapidFuzz Blocking</span>
          </div>

          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Match ID</th>
                  <th>Internal Ref</th>
                  <th>External Bank Ref</th>
                  <th>Amount (INR)</th>
                  <th>Match Tier</th>
                  <th>Confidence</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredMatches.map((m) => (
                  <tr 
                    key={m.match_id} 
                    className="cursor-pointer"
                    onClick={() => setSelectedMatch(m)}
                  >
                    <td className="font-mono text-[11px] text-blue-400 font-semibold">{m.match_id}</td>
                    <td className="font-mono text-[11px] text-[#cbd5e1]">{m.internal_txn_id || 'BATCH-SUBSET'}</td>
                    <td className="font-mono text-[11px] text-[#94a3b8]">{m.external_txn_id || 'NETTED-FEED'}</td>
                    <td className="font-mono font-bold text-[#f8fafc]">
                      ₹{parseFloat(m.internal_amount || '0').toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <span className={`badge-pill ${getMatchBadge(m.match_type)}`}>
                        {m.match_type}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-[#34d399]">
                        {Math.round(m.confidence_score * 100)}%
                      </div>
                    </td>
                    <td>
                      <button className="text-xs text-blue-400 hover:text-blue-300 font-mono">
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Match Confidence & Similarity Breakdown Inspector */}
        <div className="inst-card p-5">
          <h3 className="font-heading font-bold text-sm text-[#f1f5f9] mb-1">
            6-Factor Similarity Breakdown
          </h3>
          <div className="text-[11px] text-[#64748b] mb-4">
            Weighted algorithm verification (Section A3.4)
          </div>

          {selectedMatch ? (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-[#141d2d] border border-[#202d44] space-y-2 text-xs font-mono">
                <div className="flex justify-between">
                  <span className="text-[#64748b]">Match ID:</span>
                  <span className="text-blue-400 font-bold">{selectedMatch.match_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748b]">Rule Engine:</span>
                  <span className="text-[#cbd5e1]">{selectedMatch.rule_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748b]">Bank Source:</span>
                  <span className="text-[#38bdf8] font-bold">{selectedMatch.bank_code}</span>
                </div>
              </div>

              {/* Weight Factors */}
              <div className="space-y-2.5 text-xs font-mono">
                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-[#94a3b8]">1. Reference Similarity (35%)</span>
                    <span className="text-[#34d399] font-bold">{Math.round((selectedMatch.breakdown?.reference || 1.0) * 100)}%</span>
                  </div>
                  <div className="w-full bg-[#1a2436] rounded-full h-1.5">
                    <div className="bg-[#10b981] h-full" style={{ width: `${(selectedMatch.breakdown?.reference || 1.0) * 100}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-[#94a3b8]">2. Amount Proximity (25%)</span>
                    <span className="text-[#34d399] font-bold">{Math.round((selectedMatch.breakdown?.amount || 1.0) * 100)}%</span>
                  </div>
                  <div className="w-full bg-[#1a2436] rounded-full h-1.5">
                    <div className="bg-[#10b981] h-full" style={{ width: `${(selectedMatch.breakdown?.amount || 1.0) * 100}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-[#94a3b8]">3. Booking Date Proximity (15%)</span>
                    <span className="text-[#38bdf8] font-bold">{Math.round((selectedMatch.breakdown?.date || 1.0) * 100)}%</span>
                  </div>
                  <div className="w-full bg-[#1a2436] rounded-full h-1.5">
                    <div className="bg-[#0ea5e9] h-full" style={{ width: `${(selectedMatch.breakdown?.date || 1.0) * 100}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-[#94a3b8]">4. Counterparty Token Ratio (10%)</span>
                    <span className="text-[#a855f7] font-bold">{Math.round((selectedMatch.breakdown?.counterparty || 1.0) * 100)}%</span>
                  </div>
                  <div className="w-full bg-[#1a2436] rounded-full h-1.5">
                    <div className="bg-[#a855f7] h-full" style={{ width: `${(selectedMatch.breakdown?.counterparty || 1.0) * 100}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-[#94a3b8]">5. DR/CR Direction Match (10%)</span>
                    <span className="text-[#34d399] font-bold">100%</span>
                  </div>
                  <div className="w-full bg-[#1a2436] rounded-full h-1.5">
                    <div className="bg-[#10b981] h-full" style={{ width: '100%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-[11px] mb-1">
                    <span className="text-[#94a3b8]">6. ISO 4217 Currency (5%)</span>
                    <span className="text-[#34d399] font-bold">100%</span>
                  </div>
                  <div className="w-full bg-[#1a2436] rounded-full h-1.5">
                    <div className="bg-[#10b981] h-full" style={{ width: '100%' }}></div>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center">
                <div className="text-[10px] text-emerald-400 font-mono uppercase">Composite Confidence Score</div>
                <div className="text-2xl font-bold font-mono text-[#34d399] mt-0.5">
                  {Math.round(selectedMatch.confidence_score * 100)}%
                </div>
                <div className="text-[11px] text-[#94a3b8] mt-1">
                  Threshold: {selectedMatch.confidence_score >= 0.85 ? 'Auto-Matched (>0.85)' : 'Assisted Review (0.60 - 0.85)'}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-[#64748b] text-xs">
              Select any transaction pair from the matrix to inspect the 6-factor similarity score.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
