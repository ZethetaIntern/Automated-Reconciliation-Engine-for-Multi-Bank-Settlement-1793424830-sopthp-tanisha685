import React, { useState, useEffect } from 'react';
import { 
  Layers, Play, ShieldCheck, Clock, Zap, RefreshCw, 
  Award, FileText, Database, AlertTriangle, CheckCircle2, ChevronRight
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, onTriggerRun, isRunning, summary }) {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const ist = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false });
      const utc = now.toLocaleTimeString('en-US', { timeZone: 'UTC', hour12: false });
      setTimeStr(`${ist} IST | ${utc} UTC`);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'overview', label: 'Overview', icon: Layers },
    { id: 'matching', label: 'Matching Matrix', icon: Zap },
    { id: 'exceptions', label: 'Exception Triage (18)', icon: AlertTriangle, badge: summary?.open_exceptions },
    { id: 'audit', label: 'Cryptographic Audit', icon: ShieldCheck, valid: summary?.audit_chain_valid },
    { id: 'reconops', label: 'ReconOps Arena', icon: Award, highlight: true },
    { id: 'files', label: 'Ingestion & Formats', icon: Database },
    { id: 'reports', label: 'Compliance Reports', icon: FileText },
  ];

  return (
    <header className="border-b border-[#202b3f] bg-[#0c1017] sticky top-0 z-50">
      {/* Top Utility Bar */}
      <div className="flex items-center justify-between px-6 py-1.5 border-b border-[#182030] text-[11px] text-[#94a3b8] font-mono">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-[#10b981]">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            ENGINE: PRODUCTION ACTIVE (T+1 RECON)
          </span>
          <span className="text-[#334155]">|</span>
          <span className="flex items-center gap-1 text-[#cbd5e1]">
            <Clock size={12} className="text-[#60a5fa]" />
            {timeStr}
          </span>
          <span className="text-[#334155]">|</span>
          <span>THROUGHPUT: <strong className="text-[#f1f5f9]">142,500 rec/min</strong></span>
        </div>

        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1 text-[#34d399] bg-[#10b981]/10 px-2 py-0.5 rounded border border-[#10b981]/20">
            <ShieldCheck size={12} />
            SHA-256 CHAIN ANCHOR: VERIFIED
          </span>
          <span className="text-[#e2e8f0]">PAYBRIDGE V1.0-STABLE</span>
        </div>
      </div>

      {/* Main Nav Bar */}
      <div className="flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setActiveTab('overview')}>
            <div className="w-8 h-8 rounded bg-gradient-to-br from-[#2563eb] to-[#0ea5e9] flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/20 font-heading">
              P
            </div>
            <div>
              <div className="font-bold text-sm text-[#f8fafc] font-heading tracking-wide flex items-center gap-1.5">
                PAYBRIDGE <span className="text-[10px] bg-[#1e293b] text-[#93c5fd] px-1.5 py-0.5 rounded font-mono font-normal">RECON-OPS</span>
              </div>
              <div className="text-[10px] text-[#64748b]">Multi-Bank Settlement Guardian</div>
            </div>
          </div>

          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-[#1e293b] text-[#60a5fa] border border-[#3b82f6]/40 shadow-sm'
                      : 'text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#131b2a]'
                  } ${item.highlight && !isActive ? 'text-[#c084fc] hover:text-[#e9d5ff]' : ''}`}
                >
                  <Icon size={14} className={isActive ? 'text-[#60a5fa]' : (item.highlight ? 'text-[#c084fc]' : 'text-[#64748b]')} />
                  <span>{item.label}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="bg-[#f43f5e]/20 text-[#fb7185] border border-[#f43f5e]/30 px-1.5 py-0.2 rounded-full text-[10px] font-mono">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onTriggerRun}
            disabled={isRunning}
            className={`btn-primary shadow-lg shadow-blue-600/20 ${isRunning ? 'opacity-60 cursor-not-allowed' : ''}`}
          >
            <Play size={14} className={isRunning ? 'animate-spin' : 'fill-white'} />
            <span>{isRunning ? 'Processing Pipeline...' : 'Run Reconciliation'}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
