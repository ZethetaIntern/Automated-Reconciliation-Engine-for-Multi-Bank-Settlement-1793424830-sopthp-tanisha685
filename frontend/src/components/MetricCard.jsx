import React from 'react';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function MetricCard({ title, value, subtitle, change, isPositive, icon: Icon, color = 'blue', borderHighlight }) {
  const colorClasses = {
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    sky: 'text-sky-400 bg-sky-500/10 border-sky-500/20'
  };

  return (
    <div className={`inst-card p-4 relative overflow-hidden transition-all ${borderHighlight ? 'border-[#3b82f6]/40' : ''}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-[#94a3b8]">{title}</div>
          <div className="text-2xl font-bold font-heading text-[#f8fafc] mt-1 tracking-tight">{value}</div>
        </div>
        {Icon && (
          <div className={`p-2.5 rounded-lg border ${colorClasses[color] || colorClasses.blue}`}>
            <Icon size={18} />
          </div>
        )}
      </div>

      {(subtitle || change !== undefined) && (
        <div className="mt-3 pt-2.5 border-t border-[#1a2334] flex items-center justify-between text-xs">
          {subtitle && <span className="text-[#64748b]">{subtitle}</span>}
          {change && (
            <span className={`inline-flex items-center gap-0.5 font-mono font-medium ${
              isPositive ? 'text-[#34d399]' : (isPositive === false ? 'text-[#fb7185]' : 'text-[#94a3b8]')
            }`}>
              {isPositive === true && <ArrowUpRight size={13} />}
              {isPositive === false && <ArrowDownRight size={13} />}
              {change}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
