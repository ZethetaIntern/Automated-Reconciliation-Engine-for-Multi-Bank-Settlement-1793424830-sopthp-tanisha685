import React, { useState, useEffect } from 'react';
import { 
  Award, Play, CheckCircle2, ShieldAlert, Zap, 
  Trophy, Star, Flame, Skull, Users, ChevronRight
} from 'lucide-react';

export default function ReconOpsView() {
  const [gameState, setGameState] = useState(null);
  const [activeScenario, setActiveScenario] = useState(null);
  const [runningScenario, setRunningScenario] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);

  const fetchGameState = async () => {
    try {
      const res = await fetch('/api/v1/reconops/state');
      const data = await res.json();
      setGameState(data);
    } catch (e) {
      console.error("Failed to load ReconOps game state", e);
    }
  };

  useEffect(() => {
    fetchGameState();
  }, []);

  const handleLaunchScenario = async (scenarioId) => {
    setRunningScenario(true);
    setSimulationResult(null);
    try {
      const res = await fetch(`/api/v1/reconops/scenarios/${scenarioId}/run`, { method: 'POST' });
      const data = await res.json();
      setSimulationResult(data);
      fetchGameState(); // Refresh badges & XP
    } catch (e) {
      console.error("Scenario execution error", e);
    } finally {
      setRunningScenario(false);
    }
  };

  const getTierBadge = (tier) => {
    switch (tier) {
      case 'DIAMOND': return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
      case 'PLATINUM': return 'bg-purple-500/20 text-purple-300 border-purple-500/40';
      case 'GOLD': return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'SILVER': return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
      default: return 'bg-orange-500/20 text-orange-300 border-orange-500/40';
    }
  };

  const scenarios = gameState?.scenarios ? Object.values(gameState.scenarios) : [];
  const badges = gameState?.badges || [];
  const levels = gameState?.campaign_levels || [];
  const leaderboard = gameState?.leaderboard || [];

  return (
    <div className="space-y-6">
      {/* Player Header Banner */}
      <div className="inst-card p-6 bg-gradient-to-r from-[#12192a] via-[#161c2e] to-[#1f1738] border-[#312552] flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#8b5cf6] to-[#ec4899] flex items-center justify-center text-white text-2xl font-bold font-heading shadow-lg shadow-purple-500/30">
            ⚔️
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading font-bold text-lg text-white">ReconOps: The Settlement Guardian</h2>
              <span className="badge-pill bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px]">
                Level {gameState?.level || 7} Architect
              </span>
            </div>
            <div className="text-xs text-[#cbd5e1] mt-1">
              {gameState?.company || "PayBridge Technologies"} • Processing {gameState?.daily_volume || "2.1M Daily Txns"} across 7 Banking Partners
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 font-mono">
          <div className="text-right">
            <div className="text-[10px] uppercase text-[#a78bfa]">Experience Points</div>
            <div className="text-2xl font-bold text-[#f8fafc] flex items-center gap-1 justify-end">
              <Flame size={20} className="text-amber-400 fill-amber-400" />
              {gameState?.player_xp || 4850} <span className="text-xs text-[#94a3b8]">XP</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase text-[#a78bfa]">Badges Unlocked</div>
            <div className="text-2xl font-bold text-[#38bdf8] flex items-center gap-1 justify-end">
              <Trophy size={18} className="text-yellow-400" />
              {gameState?.badges_unlocked || "17/20"}
            </div>
          </div>
        </div>
      </div>

      {/* 6 Real-World Banking Failure Case Study Boss Battles */}
      <div className="inst-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-heading font-bold text-sm text-[#f1f5f9] flex items-center gap-2">
              <Skull size={16} className="text-rose-400" />
              Real-World Failure Simulations (Case Studies C1 - C6)
            </h3>
            <div className="text-[11px] text-[#64748b]">Stress-test algorithms against historical production disasters</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((scen) => (
            <div
              key={scen.id}
              className="p-4 rounded-xl bg-[#121824] border border-[#1e283c] hover:border-[#384968] flex flex-col justify-between transition-all"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold">
                    {scen.category}
                  </span>
                  <span className="text-xs font-mono text-amber-400 font-bold">+{scen.xp_reward} XP</span>
                </div>

                <div className="font-heading font-bold text-sm text-[#f1f5f9] mb-1.5">{scen.title}</div>
                <div className="text-xs text-[#94a3b8] mb-3 leading-relaxed">{scen.story}</div>

                <div className="p-2.5 rounded-lg bg-[#0c1018] border border-[#192233] text-[11px] text-[#38bdf8] mb-3">
                  <strong>Challenge:</strong> {scen.challenge}
                </div>
              </div>

              <button
                onClick={() => handleLaunchScenario(scen.id)}
                disabled={runningScenario}
                className="w-full btn-secondary text-xs py-2 justify-center hover:bg-blue-600 hover:text-white"
              >
                <Play size={12} className="fill-current" />
                <span>Launch Simulation Battle</span>
              </button>
            </div>
          ))}
        </div>

        {/* Battle Result Popover */}
        {simulationResult && (
          <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 animate-in fade-in slide-in-from-bottom">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm font-heading">
                <CheckCircle2 size={18} />
                SIMULATION CONQUERED: {simulationResult.title}
              </div>
              <span className="font-mono text-xs text-amber-400 font-bold">+{simulationResult.xp_earned} XP Awarded</span>
            </div>
            <div className="text-xs text-emerald-200/80 mt-1">
              Processed {simulationResult.simulation_metrics?.dataset_records_evaluated} simulated transactions. Caught {simulationResult.simulation_metrics?.planted_exceptions_trapped} planted exceptions with {simulationResult.simulation_metrics?.accuracy_score} accuracy.
            </div>
          </div>
        )}
      </div>

      {/* 20 Achievement Badges across 5 Tiers */}
      <div className="inst-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-heading font-bold text-sm text-[#f1f5f9] flex items-center gap-2">
              <Trophy size={16} className="text-amber-400" />
              20 Achievement Badges (Section B2.2)
            </h3>
            <div className="text-[11px] text-[#64748b]">Bronze • Silver • Gold • Platinum • Diamond Tiers</div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {badges.map((b) => (
            <div
              key={b.id}
              className={`p-3 rounded-xl border text-center flex flex-col justify-between transition-all ${
                b.unlocked
                  ? 'bg-[#141c2c] border-[#253654] shadow-md'
                  : 'bg-[#0e131d]/60 border-[#1a2333] opacity-40'
              }`}
            >
              <div>
                <div className="text-2xl mb-1.5">{b.icon}</div>
                <div className="font-heading font-bold text-xs text-[#f1f5f9]">{b.name}</div>
                <div className={`badge-pill text-[9px] mt-1 border ${getTierBadge(b.tier)}`}>
                  {b.tier}
                </div>
                <div className="text-[10px] text-[#94a3b8] mt-2 leading-tight">{b.description}</div>
              </div>

              <div className="mt-3 pt-2 border-t border-[#1a2334] text-[10px] font-mono text-[#64748b]">
                {b.unlocked ? `Unlocked` : 'Locked'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Campaign 7-Day Journey & Arena Leaderboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Campaign Map */}
        <div className="inst-card p-5">
          <h3 className="font-heading font-bold text-sm text-[#f1f5f9] mb-1">
            7-Level Campaign Progression
          </h3>
          <div className="text-[11px] text-[#64748b] mb-4">Day-by-day complexity evolution</div>

          <div className="space-y-2.5">
            {levels.map((lvl) => (
              <div
                key={lvl.level}
                className={`p-3 rounded-lg border flex items-center justify-between text-xs ${
                  lvl.completed
                    ? 'bg-[#121927] border-emerald-500/30 text-[#f1f5f9]'
                    : (lvl.unlocked ? 'bg-[#151d2f] border-blue-500/40 text-[#f1f5f9]' : 'bg-[#0c1017] border-[#182030] text-[#64748b]')
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-[10px] font-mono ${
                    lvl.completed ? 'bg-emerald-500 text-black' : (lvl.unlocked ? 'bg-blue-600 text-white' : 'bg-[#1e293b] text-[#64748b]')
                  }`}>
                    {lvl.level}
                  </span>
                  <div>
                    <div className="font-semibold text-xs">{lvl.title}</div>
                    <div className="text-[10px] text-[#94a3b8]">{lvl.description}</div>
                  </div>
                </div>

                <div className="font-mono text-right">
                  <div className="text-amber-400 font-bold">+{lvl.xp} XP</div>
                  <div className="text-[10px] text-[#64748b]">{lvl.completed ? '100% Passed' : 'Active'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Arena Leaderboard */}
        <div className="inst-card p-5">
          <h3 className="font-heading font-bold text-sm text-[#f1f5f9] mb-1 flex items-center gap-2">
            <Users size={16} className="text-blue-400" />
            Arena Global Leaderboard
          </h3>
          <div className="text-[11px] text-[#64748b] mb-4">Ranked by accuracy, processing speed, and code quality</div>

          <div className="space-y-2 font-mono text-xs">
            {leaderboard.map((item) => (
              <div
                key={item.rank}
                className={`p-3 rounded-lg border flex items-center justify-between ${
                  item.rank === 1
                    ? 'bg-blue-600/10 border-blue-500/40 text-blue-300'
                    : 'bg-[#121824] border-[#1c2638] text-[#cbd5e1]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="font-bold text-sm w-4 text-[#94a3b8]">#{item.rank}</span>
                  <div>
                    <div className="font-bold font-sans text-xs text-[#f1f5f9]">{item.username}</div>
                    <div className="text-[10px] text-[#64748b]">{item.status}</div>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-right">
                  <div>
                    <div className="text-[#34d399] font-bold">{item.accuracy}</div>
                    <div className="text-[10px] text-[#64748b]">Accuracy</div>
                  </div>
                  <div>
                    <div className="text-amber-400 font-bold">{item.xp}</div>
                    <div className="text-[10px] text-[#64748b]">Total XP</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
