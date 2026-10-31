"""
ReconOps Game Engine: Campaign Mode, Badges, Leaderboards, and XP Progression.
Strictly implements Section B2 Experience Points and 20 Badges across 5 tiers.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from backend.app.reconops.scenarios import SCENARIOS


class Badge(BaseModel):
    id: str
    name: str
    tier: str  # BRONZE, SILVER, GOLD, PLATINUM, DIAMOND
    category: str
    description: str
    icon: str
    unlocked: bool = False
    unlocked_at: Optional[str] = None


ALL_BADGES: List[Badge] = [
    # Bronze (5)
    Badge(id="FIRST_PARSE", name="First Parse", tier="BRONZE", category="Ingestion", description="Parse any bank statement format successfully.", icon="📄", unlocked=True, unlocked_at="2026-03-30T10:00:00Z"),
    Badge(id="FIRST_MATCH", name="First Match", tier="BRONZE", category="Matching", description="Achieve your first exact composite match.", icon="🎯", unlocked=True, unlocked_at="2026-03-30T10:05:00Z"),
    Badge(id="EXCEPTION_SPOTTER", name="Exception Spotter", tier="BRONZE", category="Exceptions", description="Identify and classify your first reconciliation exception.", icon="🔍", unlocked=True, unlocked_at="2026-03-30T10:10:00Z"),
    Badge(id="BUG_HUNTER", name="Bug Hunter", tier="BRONZE", category="Quality", description="Find and resolve planted deliberate errors.", icon="🐛", unlocked=True, unlocked_at="2026-03-30T10:15:00Z"),
    Badge(id="FORMAT_WHISPERER", name="Format Whisperer", tier="BRONZE", category="Ingestion", description="Successfully parse all 3 primary banking formats (CSV, MT940, CAMT.053).", icon="📑", unlocked=True, unlocked_at="2026-03-30T10:20:00Z"),

    # Silver (5)
    Badge(id="SPEED_DEMON", name="Speed Demon", tier="SILVER", category="Performance", description="Process 100,000 records in under 60 seconds.", icon="⚡", unlocked=True, unlocked_at="2026-03-30T10:25:00Z"),
    Badge(id="FUZZY_MASTER", name="Fuzzy Logic Master", tier="SILVER", category="Matching", description="Achieve > 90% accuracy on fuzzy reference matching.", icon="🧠", unlocked=True, unlocked_at="2026-03-30T10:30:00Z"),
    Badge(id="RULE_ENGINEER", name="Rule Engineer", tier="SILVER", category="Matching", description="Successfully execute split & netted settlement subset solvers.", icon="📐", unlocked=True, unlocked_at="2026-03-30T10:35:00Z"),
    Badge(id="AUDIT_COMPLETE", name="Audit Trail Complete", tier="SILVER", category="Compliance", description="Maintain zero cryptographic hash chain corruptions.", icon="🔒", unlocked=True, unlocked_at="2026-03-30T10:40:00Z"),
    Badge(id="API_ARCHITECT", name="API Architect", tier="SILVER", category="Integration", description="Connect all 8 FastAPI production endpoints.", icon="🌐", unlocked=True, unlocked_at="2026-03-30T10:45:00Z"),

    # Gold (5)
    Badge(id="ZERO_LEAK", name="Zero Exception Leak", tier="GOLD", category="Quality", description="Catch 100% of planted exceptions in a production test batch.", icon="🛡️", unlocked=False),
    Badge(id="PERF_OPTIMIZER", name="Performance Optimiser", tier="GOLD", category="Performance", description="Beat baseline processing latency by > 50%.", icon="🚀", unlocked=True, unlocked_at="2026-03-30T10:50:00Z"),
    Badge(id="DB_ARCHITECT", name="Database Architect", tier="GOLD", category="Storage", description="Deploy partitioned database schema with composite indexes.", icon="💾", unlocked=True, unlocked_at="2026-03-30T10:52:00Z"),
    Badge(id="SECURITY_GUARDIAN", name="Security Guardian", tier="GOLD", category="Security", description="Enforce full PCI DSS PAN masking and RBAC on all endpoints.", icon="🛡️", unlocked=True, unlocked_at="2026-03-30T10:55:00Z"),
    Badge(id="TEST_CHAMPION", name="Test Coverage Champion", tier="GOLD", category="Quality", description="Achieve > 85% automated test coverage across all modules.", icon="🏆", unlocked=True, unlocked_at="2026-03-30T10:58:00Z"),

    # Platinum (3)
    Badge(id="PRODUCTION_READY", name="Production Ready", tier="PLATINUM", category="DevOps", description="Pass all end-to-end integration and chaos scenarios.", icon="🌟", unlocked=True, unlocked_at="2026-03-30T11:00:00Z"),
    Badge(id="FULL_PIPELINE", name="Full Pipeline", tier="PLATINUM", category="Architecture", description="Deploy full 4-stage automated pipeline with live dashboard.", icon="👑", unlocked=True, unlocked_at="2026-03-30T11:05:00Z"),
    Badge(id="CODE_REVIEWER", name="Code Reviewer", tier="PLATINUM", category="Process", description="Complete comprehensive code review and architecture documentation.", icon="📜", unlocked=False),

    # Diamond (2)
    Badge(id="INNOVATION_AWARD", name="Innovation Award", tier="DIAMOND", category="Innovation", description="Implement candidate-blocked subset-sum netting algorithm.", icon="💎", unlocked=True, unlocked_at="2026-03-30T11:10:00Z"),
    Badge(id="PERFECT_SCORE", name="Perfect Score", tier="DIAMOND", category="Excellence", description="Achieve 100% on the Finance Ops Review final production audit.", icon="💠", unlocked=False),
]


CAMPAIGN_LEVELS = [
    {
        "level": 1,
        "title": "Level 1: Single-Bank Ingestion",
        "bank": "HDFC",
        "format": "CSV",
        "description": "Parse 25,000 HDFC settlement records and achieve initial exact composite matches.",
        "xp": 300,
        "unlocked": True,
        "completed": True,
        "score": 98.4
    },
    {
        "level": 2,
        "title": "Level 2: SWIFT MT940 Deviations",
        "bank": "AXIS & SBI",
        "format": "MT940",
        "description": "Parse MT940 state machine with period decimals and missing funds codes.",
        "xp": 450,
        "unlocked": True,
        "completed": True,
        "score": 96.8
    },
    {
        "level": 3,
        "title": "Level 3: ISO 20022 Multi-Bank XML",
        "bank": "KOTAK",
        "format": "CAMT.053",
        "description": "Ingest deep nested <NtryDtls>/<TxDtls> XML structures with XPath expressions.",
        "xp": 600,
        "unlocked": True,
        "completed": True,
        "score": 95.2
    },
    {
        "level": 4,
        "title": "Level 4: Cross-Currency FX Netting",
        "bank": "GLOBAL_UK",
        "format": "MT940 / CSV",
        "description": "Reconcile INR vs GBP batches within 1.5% FX tolerance band using RBI benchmark rates.",
        "xp": 750,
        "unlocked": True,
        "completed": True,
        "score": 94.6
    },
    {
        "level": 5,
        "title": "Level 5: Split & Netted Settlements",
        "bank": "PAYBRIDGE_NET",
        "format": "MULTI",
        "description": "Solve subset-sum optimization to match 1-to-N splits and N-to-1 batch netted entries.",
        "xp": 900,
        "unlocked": True,
        "completed": True,
        "score": 97.1
    },
    {
        "level": 6,
        "title": "Level 6: 18-Category Exception Triage",
        "bank": "ALL_BANKS",
        "format": "ALL",
        "description": "Classify all 18 exception categories and auto-resolve Tier 1 duplicates & fee variances.",
        "xp": 1100,
        "unlocked": True,
        "completed": True,
        "score": 99.1
    },
    {
        "level": 7,
        "title": "Level 7: Boss Battle - Finance Ops Review",
        "bank": "7_PARTNERS",
        "format": "ALL",
        "description": "Final 500,000-record production stress test with deliberate corruption & SLA pressure.",
        "xp": 1500,
        "unlocked": True,
        "completed": False,
        "score": 0.0
    }
]


LEADERBOARD = [
    {"rank": 1, "username": "tanisha_lead", "xp": 4850, "accuracy": "99.7%", "speed_sec": "4.2s", "exceptions_resolved": 842, "status": "Lead Architect (You)"},
    {"rank": 2, "username": "rahul_fintech", "xp": 4620, "accuracy": "98.9%", "speed_sec": "6.1s", "exceptions_resolved": 810, "status": "Senior Quant"},
    {"rank": 3, "username": "ananya_quant", "xp": 4410, "accuracy": "98.2%", "speed_sec": "7.8s", "exceptions_resolved": 795, "status": "Recon Specialist"},
    {"rank": 4, "username": "vikram_systems", "xp": 4180, "accuracy": "97.5%", "speed_sec": "9.4s", "exceptions_resolved": 760, "status": "DevOps Engineer"},
    {"rank": 5, "username": "priya_audit", "xp": 3950, "accuracy": "96.8%", "speed_sec": "11.2s", "exceptions_resolved": 730, "status": "Compliance Lead"},
]


class ReconOpsManager:
    """
    Manages game progression, player stats, badge unlocks, and scenario battle execution.
    """

    def __init__(self):
        self.player_xp = 4850
        self.current_level = 7
        self.badges = ALL_BADGES
        self.levels = CAMPAIGN_LEVELS
        self.leaderboard = LEADERBOARD

    def get_game_state(self) -> Dict[str, Any]:
        unlocked_count = len([b for b in self.badges if b.unlocked])
        return {
            "player_name": "Tanisha (Engineering Lead)",
            "company": "PayBridge Technologies",
            "daily_volume": "2.1 Million Txns",
            "player_xp": self.player_xp,
            "level": self.current_level,
            "level_title": "Principal Settlement Guardian",
            "badges_unlocked": f"{unlocked_count}/{len(self.badges)}",
            "badges": [b.model_dump() for b in self.badges],
            "campaign_levels": self.levels,
            "leaderboard": self.leaderboard,
            "scenarios": SCENARIOS
        }


global_reconops_manager = ReconOpsManager()
