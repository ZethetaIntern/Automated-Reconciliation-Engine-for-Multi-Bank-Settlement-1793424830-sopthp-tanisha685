import React from 'react';
import { 
  TrendingUp, CheckCircle, AlertTriangle, ShieldCheck, 
  DollarSign, Zap, Clock, Building2, Activity, ArrowRight
} from 'lucide-react';
import MetricCard from '../components/MetricCard';
import PipelineVisualizer from '../components/PipelineVisualizer';

export default function OverviewView({ summary, onTriggerRun, setActiveTab, setSelectedException }) {
  const bankList = summary?.bank_breakdown || [];
  const anomalies = summary?.active_anomalies || [];

  return (
    <div className="space-y-6">
      {/* Active Anomaly Alerts (Citibank Revlon / Whale Alert & Feed Absence) */}
      {anomalies.length > 0 && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start justify-between gap-4 animate-in slide-in-from-top">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded bg-rose-500/20 text-rose-400 mt-0.5">
              <AlertTriangle size={18} />
            </div>
            <div>
              <div className="font-heading font-bold text-sm text-rose-200 flex items-center gap-2">
                CRITICAL ANOMALY DETECTED: {anomalies[0].rule}
                <span className="badge-pill badge-critical text-[10px]">{anomalies[0].severity}</span>
              </div>
              <div className="text-xs text-rose-300/80 mt-1">{anomalies[0].description}</div>
              <div className="text-[11px] font-mono text-rose-400 mt-1.5 flex items-center gap-2">
                <span>Recommendation: {anomalies[0].recommendation}</span>
              </div>
            </div>
          </div>
          <button 
            onClick={() => setActiveTab('exceptions')}
            className="btn-danger text-xs whitespace-nowrap"
          >
            Triage Exception
          </button>
        </div>
      )}

      {/* Primary KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Reconciled Volume"
          value={summary?.total_reconciled_value_inr || "₹48.25 Cr"}
          subtitle="T+1 Settlement Window"
          change="+14.2% vs yesterday"
          isPositive={true}
          icon={DollarSign}
          color="emerald"
        />

        <MetricCard
          title="Overall Match Accuracy"
          value={`${summary?.overall_match_rate || 98.6}%`}
          subtitle={`Exact: ${summary?.exact_match_rate || 82.5}% | Fuzzy: ${summary?.fuzzy_match_rate || 10.2}%`}
          change="+0.8% above SLA target"
          isPositive={true}
          icon={CheckCircle}
          color="blue"
        />

        <MetricCard
          title="Open Exceptions"
          value={summary?.open_exceptions || 54}
          subtitle={`Auto-Resolved: ${summary?.auto_resolved_exceptions || 162}`}
          change={`${summary?.critical_exceptions || 4} Critical SLA items`}
          isPositive={false}
          icon={AlertTriangle}
          color="rose"
        />

        <MetricCard
          title="SLA Compliance Rate"
          value={`${summary?.sla_compliance_rate || 99.1}%`}
          subtitle="RBI Master Direction T+1"
          change="Zero Statutory Fines"
          isPositive={true}
          icon={ShieldCheck}
          color="purple"
        />
      </div>

      {/* 4-Stage Reconciliation Pipeline Visualizer */}
      <PipelineVisualizer runData={summary} />

      {/* Bank Settlement Health Matrix & Hourly Throughput */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bank Performance Matrix */}
        <div className="lg:col-span-2 inst-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-heading font-bold text-sm text-[#f1f5f9] flex items-center gap-2">
                <Building2 size={16} className="text-blue-400" />
                Banking Partner Settlement Matrix
              </h3>
              <div className="text-[11px] text-[#64748b]">Per-bank match rate, format deviations, and SLA metrics</div>
            </div>
            <button onClick={() => setActiveTab('files')} className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
              View Bank Configs <ArrowRight size={12} />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bank Partner</th>
                  <th>Format Standard</th>
                  <th>Match Rate</th>
                  <th>Open Exceptions</th>
                  <th>SLA Compliance</th>
                  <th>Feed Health</th>
                </tr>
              </thead>
              <tbody>
                {bankList.map((b) => (
                  <tr key={b.bank_code}>
                    <td className="font-semibold text-[#f8fafc] flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                      {b.bank_name} ({b.bank_code})
                    </td>
                    <td className="font-mono text-[11px] text-[#94a3b8]">{b.format}</td>
                    <td className="font-mono font-bold text-[#34d399]">{b.match_rate}%</td>
                    <td className="font-mono">{b.exceptions} items</td>
                    <td className="font-mono text-[#60a5fa]">{b.sla_compliance}%</td>
                    <td>
                      <span className={`badge-pill ${b.status === 'OPTIMAL' ? 'badge-exact' : 'badge-rule'}`}>
                        {b.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Algorithm Match Distribution */}
        <div className="inst-card p-5 flex flex-col justify-between">
          <div>
            <h3 className="font-heading font-bold text-sm text-[#f1f5f9] flex items-center gap-2 mb-1">
              <Zap size={16} className="text-amber-400" />
              Matching Layer Breakdown
            </h3>
            <div className="text-[11px] text-[#64748b]">Sequential 3-stage resolution distribution</div>

            <div className="space-y-3 mt-4 text-xs font-mono">
              <div>
                <div className="flex justify-between text-[#cbd5e1] mb-1">
                  <span>STAGE 1: EXACT HASH (O(N+M))</span>
                  <span className="text-[#34d399] font-bold">{summary?.exact_match_rate || 82.5}%</span>
                </div>
                <div className="w-full bg-[#182335] rounded-full h-2 overflow-hidden">
                  <div className="bg-[#10b981] h-full" style={{ width: `${summary?.exact_match_rate || 82.5}%` }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#cbd5e1] mb-1">
                  <span>STAGE 2: RAPIDFUZZ BLOCKING</span>
                  <span className="text-[#38bdf8] font-bold">{summary?.fuzzy_match_rate || 10.2}%</span>
                </div>
                <div className="w-full bg-[#182335] rounded-full h-2 overflow-hidden">
                  <div className="bg-[#0ea5e9] h-full" style={{ width: `${summary?.fuzzy_match_rate || 10.2}%` }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#cbd5e1] mb-1">
                  <span>STAGE 3: RULES / SUBSET-SUM</span>
                  <span className="text-[#fbbf24] font-bold">{summary?.rule_match_rate || 5.7}%</span>
                </div>
                <div className="w-full bg-[#182335] rounded-full h-2 overflow-hidden">
                  <div className="bg-[#f59e0b] h-full" style={{ width: `${summary?.rule_match_rate || 5.7}%` }}></div>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-[#1e293b] flex items-center justify-between text-xs">
            <span className="text-[#94a3b8]">Average Matching Latency:</span>
            <span className="font-mono font-bold text-[#f1f5f9]">{summary?.avg_processing_time_ms || 385.4} ms</span>
          </div>
        </div>
      </div>
    </div>
  );
}
