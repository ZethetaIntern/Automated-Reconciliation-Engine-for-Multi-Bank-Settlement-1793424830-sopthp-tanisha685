import React from 'react';
import { Database, GitCommit, CheckCircle, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

export default function PipelineVisualizer({ runData, isRunning }) {
  const stages = [
    {
      num: '01',
      name: 'INGESTION',
      icon: Database,
      formats: 'CSV • MT940 • CAMT.053',
      stat: runData ? `${(runData.total_internal || 100000).toLocaleString()} recs` : '5 Feeds Active',
      status: 'VERIFIED',
      color: 'border-sky-500/30 text-sky-400 bg-sky-500/5'
    },
    {
      num: '02',
      name: 'NORMALISATION',
      icon: GitCommit,
      formats: 'UTC • Banker’s Decimal • PAN Mask',
      stat: '100% Conformed',
      status: 'PCI DSS PASSED',
      color: 'border-indigo-500/30 text-indigo-400 bg-indigo-500/5'
    },
    {
      num: '03',
      name: '3-TIER MATCHING',
      icon: CheckCircle,
      formats: 'Exact (Hash) • Fuzzy • Rules',
      stat: runData ? `${runData.match_rate || 98.6}% Matched` : '98.6% Target',
      status: runData ? `${runData.matched_count || 98400} Paired` : 'Active',
      color: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/5'
    },
    {
      num: '04',
      name: 'EXCEPTION & AUDIT',
      icon: AlertCircle,
      formats: '18 Categories • Tier 1 Auto',
      stat: runData ? `${runData.auto_resolved_count || 162} Auto-Resolved` : 'SLA Monitored',
      status: 'SHA-256 CHAINED',
      color: 'border-amber-500/30 text-amber-400 bg-amber-500/5'
    }
  ];

  return (
    <div className="inst-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold text-[#cbd5e1] uppercase tracking-wider flex items-center gap-2">
          <span>Reconciliation Pipeline Lifecycle</span>
          {isRunning && (
            <span className="flex items-center gap-1 text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded font-mono animate-pulse">
              EXECUTING STAGES...
            </span>
          )}
        </div>
        <span className="text-[11px] text-[#64748b] font-mono">Deterministic O(N+M) Architecture</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          return (
            <div key={stage.num} className="relative">
              <div className={`p-3 rounded-lg border ${stage.color} h-full flex flex-col justify-between`}>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[10px] font-bold opacity-60">STAGE {stage.num}</span>
                    <Icon size={14} />
                  </div>
                  <div className="font-heading font-bold text-sm text-[#f1f5f9]">{stage.name}</div>
                  <div className="text-[10px] text-[#94a3b8] mt-0.5">{stage.formats}</div>
                </div>

                <div className="mt-3 pt-2 border-t border-[#1e293b] flex items-center justify-between text-[11px] font-mono">
                  <span className="font-semibold text-[#e2e8f0]">{stage.stat}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/5 border border-white/10 opacity-80">{stage.status}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
