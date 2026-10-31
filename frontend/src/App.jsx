import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import RunModal from './components/RunModal';
import ExceptionDrawer from './components/ExceptionDrawer';
import OverviewView from './views/OverviewView';
import MatchingView from './views/MatchingView';
import ExceptionsView from './views/ExceptionsView';
import AuditView from './views/AuditView';
import ReconOpsView from './views/ReconOpsView';
import FilesView from './views/FilesView';
import ReportsView from './views/ReportsView';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [summary, setSummary] = useState(null);
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedException, setSelectedException] = useState(null);

  const fetchSummary = async () => {
    try {
      const res = await fetch('/api/v1/dashboard/summary');
      const data = await res.json();
      setSummary(data);
    } catch (e) {
      console.error("Failed to fetch dashboard summary", e);
    }
  };

  useEffect(() => {
    fetchSummary();
    const interval = setInterval(fetchSummary, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleExecuteRun = async (params) => {
    setIsRunning(true);
    setIsRunModalOpen(false);
    try {
      const res = await fetch('/api/v1/reconciliation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      const data = await res.json();
      fetchSummary();
      // Switch to overview or matching tab
      setActiveTab('overview');
    } catch (e) {
      console.error("Reconciliation run execution failed", e);
    } finally {
      setIsRunning(false);
    }
  };

  const handleResolveException = async (exceptionId, resolutionData) => {
    try {
      const res = await fetch(`/api/v1/exceptions/${exceptionId}/resolve`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(resolutionData)
      });
      const data = await res.json();
      setSelectedException(null);
      fetchSummary();
    } catch (e) {
      console.error("Resolution failed", e);
    }
  };

  return (
    <div className="min-h-screen bg-[#090c10] text-[#f1f5f9] flex flex-col font-sans">
      {/* Institutional Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onTriggerRun={() => setIsRunModalOpen(true)}
        isRunning={isRunning}
        summary={summary}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === 'overview' && (
          <OverviewView
            summary={summary}
            onTriggerRun={() => setIsRunModalOpen(true)}
            setActiveTab={setActiveTab}
            setSelectedException={setSelectedException}
          />
        )}

        {activeTab === 'matching' && (
          <MatchingView runs={summary} onSelectMatch={(m) => {}} />
        )}

        {activeTab === 'exceptions' && (
          <ExceptionsView onSelectException={(exc) => setSelectedException(exc)} />
        )}

        {activeTab === 'audit' && (
          <AuditView />
        )}

        {activeTab === 'reconops' && (
          <ReconOpsView />
        )}

        {activeTab === 'files' && (
          <FilesView />
        )}

        {activeTab === 'reports' && (
          <ReportsView />
        )}
      </main>

      {/* Trigger Run Modal */}
      <RunModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        onExecute={handleExecuteRun}
        isRunning={isRunning}
      />

      {/* Exception Resolution Drawer */}
      <ExceptionDrawer
        exception={selectedException}
        onClose={() => setSelectedException(null)}
        onResolve={handleResolveException}
      />

      {/* Institutional Footer */}
      <footer className="border-t border-[#1a2334] py-4 px-6 text-center text-xs text-[#64748b] font-mono flex items-center justify-between">
        <div>
          PayBridge Settlement Guardian v1.0 • Engineered for Zetheta Multi-Bank Reconciliation
        </div>
        <div className="flex items-center gap-4 text-[11px]">
          <span>PCI DSS Compliant</span>
          <span>•</span>
          <span>RBI Master Direction T+1</span>
          <span>•</span>
          <span>Companies Act Sec 128 Chained Audit</span>
        </div>
      </footer>
    </div>
  );
}
