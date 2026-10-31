"""
Real-world Case Study Scenarios and Boss Battles for ReconOps.
Encapsulates all 6 real-world banking failures from Part C.
"""

from typing import Dict, Any, List


SCENARIOS: Dict[str, Dict[str, Any]] = {
    "C1_PAYTM": {
        "id": "C1_PAYTM",
        "title": "The Exception Avalanche (Paytm Crisis 2024)",
        "category": "Real-Time vs Batch Processing",
        "story": "Paytm Payments Bank accumulated 2 million unresolved exceptions over 18 months due to slow 24-hour batch cycles. Fast-moving UPI velocity paralyzed back-office operations.",
        "trigger": "Exception backlog exceeds 10,000 items with SLA breaches.",
        "challenge": "Activate Streaming / Fast-Mode Reconciliation, auto-resolve Tier 1 duplicates, and triage critical items within 15 minutes.",
        "dataset_size": 25000,
        "planted_exceptions": 340,
        "xp_reward": 450,
        "badge_id": "SPEED_DEMON"
    },
    "C2_CITIBANK": {
        "id": "C2_CITIBANK",
        "title": "The Whale Transaction (Citibank Revlon 2020)",
        "category": "Anomaly Detection & Dual Auth",
        "story": "Citibank accidentally wired US$893M instead of $7.8M interest because wire reconciliation only verified instruction matching rather than reasonableness against historical averages.",
        "trigger": "Single transaction amount > 100x historical counterparty average (Z-score > 12).",
        "challenge": "Trigger the Whale Anomaly Alert, block auto-matching, and enforce mandatory Dual-Authorisation before clearance.",
        "dataset_size": 5000,
        "planted_exceptions": 12,
        "xp_reward": 500,
        "badge_id": "INNOVATION_AWARD"
    },
    "C3_NPCI": {
        "id": "C3_NPCI",
        "title": "The Penny Drift (NPCI UPI Rounding 2022)",
        "category": "Fixed-Point Decimal Arithmetic",
        "story": "Banks using IEEE 754 floating-point math accumulated crores of rounding drift against NPCI's banker's rounding settlement engine.",
        "trigger": "Cumulative float drift > ₹1 Lakh across 50,000 micro-transactions.",
        "challenge": "Verify that all monetary calculations strictly use Decimal with ROUND_HALF_EVEN and zero floating-point imprecision.",
        "dataset_size": 50000,
        "planted_exceptions": 85,
        "xp_reward": 400,
        "badge_id": "PERFECT_SCORE"
    },
    "C4_WIRECARD": {
        "id": "C4_WIRECARD",
        "title": "The Phantom Settlement (Wirecard AG 2020)",
        "category": "Cryptographic File Integrity",
        "story": "Wirecard fabricated €1.9B in escrow balances using unverified spreadsheets without direct SFTP bank feeds or cryptographic checksums.",
        "trigger": "Bank file hash checksum mismatch / altered settlement payload.",
        "challenge": "Detect tampered bank settlement file using SHA-256 digital fingerprinting and verify the immutable append-only audit trail.",
        "dataset_size": 10000,
        "planted_exceptions": 50,
        "xp_reward": 600,
        "badge_id": "SECURITY_GUARDIAN"
    },
    "C5_YESBANK": {
        "id": "C5_YESBANK",
        "title": "The Frozen Funds (Yes Bank Moratorium 2020)",
        "category": "Two-Layer Balance Reconciliation",
        "story": "During the RBI moratorium, settlement files were generated but funds could not move. Transaction recon passed while balance recon failed completely.",
        "trigger": "Transaction matching succeeds, but Bank Opening + Net Txns != Closing Balance.",
        "challenge": "Implement Dual-Layer Reconciliation (Transaction-Level + Balance-Level :60F:/:62F:) to catch phantom liquidity freezes.",
        "dataset_size": 15000,
        "planted_exceptions": 60,
        "xp_reward": 550,
        "badge_id": "PRODUCTION_READY"
    },
    "C6_TARGET": {
        "id": "C6_TARGET",
        "title": "The Silent Leak (Target POS Breach 2013)",
        "category": "PCI DSS Compliance & PAN Masking",
        "story": "40M credit cards were stolen through POS malware while financial reconciliation passed normally because transactions were genuine.",
        "trigger": "Unmasked PAN numbers detected in narration/reference fields.",
        "challenge": "Enforce PCI DSS Requirement 3.3 PAN masking (show only last 4 digits) and data transmission volume anomaly alerts.",
        "dataset_size": 12000,
        "planted_exceptions": 40,
        "xp_reward": 450,
        "badge_id": "FORMAT_WHISPERER"
    }
}
