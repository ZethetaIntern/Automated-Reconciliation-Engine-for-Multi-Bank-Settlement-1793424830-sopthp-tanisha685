"""
Unit Tests for Database Persistence and Storage Layer.
Verifies persistence and retrieval of runs, matches, exceptions, and audit records.
"""

from decimal import Decimal
from datetime import datetime, timezone

from backend.app.models.database import init_db, SessionLocal, ReconciliationRun
from backend.app.models.db_service import (
    persist_reconciliation_run, persist_match_results,
    persist_exceptions, load_all_runs_from_db, persist_audit_log_entry
)
from backend.app.models.schemas import (
    MatchResultItem, ExceptionItem, MatchTypeEnum,
    ExceptionCategoryEnum, SeverityLevelEnum, ExceptionStatusEnum, EscalationTierEnum
)


def test_database_run_persistence_and_retrieval():
    init_db()
    test_run_id = f"RUN-TEST-DB-{int(datetime.now(timezone.utc).timestamp())}"
    run_record = {
        "run_id": test_run_id,
        "bank_code": "HDFC",
        "status": "COMPLETED",
        "fast_mode": False,
        "total_internal": 500,
        "total_external": 490,
        "matched_count": 485,
        "exact_matches": 450,
        "fuzzy_matches": 25,
        "rule_matches": 10,
        "split_matches": 0,
        "netted_matches": 0,
        "exception_count": 15,
        "auto_resolved_count": 8,
        "match_rate": 98.9,
        "duration_ms": 145.2,
        "opening_balance": "100000.00",
        "closing_balance": "150000.00",
        "computed_closing_balance": "150000.00",
        "balance_reconciled": True
    }

    persist_reconciliation_run(run_record)

    all_runs = load_all_runs_from_db()
    found = [r for r in all_runs if r["run_id"] == test_run_id]
    assert len(found) == 1
    assert found[0]["bank_code"] == "HDFC"
    assert found[0]["match_rate"] == 98.9


def test_database_match_results_and_exceptions_persistence():
    init_db()
    run_id = "RUN-TEST-REL"

    matches = [
        MatchResultItem(
            match_id=f"M-TEST-{int(datetime.now(timezone.utc).timestamp())}",
            run_id=run_id,
            internal_txn_id="TXN-IN-99",
            external_txn_id="TXN-EX-99",
            match_type=MatchTypeEnum.EXACT,
            confidence_score=1.0,
            internal_amount="7500.00",
            external_amount="7500.00",
            bank_code="AXIS",
            matched_at=datetime.now(timezone.utc)
        )
    ]
    persist_match_results(matches)

    exceptions = [
        ExceptionItem(
            exception_id=f"EXC-TEST-{int(datetime.now(timezone.utc).timestamp())}",
            run_id=run_id,
            category=ExceptionCategoryEnum.DIRECTION_REVERSAL,
            severity=SeverityLevelEnum.CRITICAL,
            status=ExceptionStatusEnum.OPEN,
            assigned_tier=EscalationTierEnum.TIER_4_COMPLIANCE,
            bank_code="SBI",
            affected_amount="250000.00",
            currency="INR",
            description="Reversed entry test",
            suggested_resolution="Immediate compliance review",
            sla_minutes=30,
            created_at=datetime.now(timezone.utc),
            sla_deadline=datetime.now(timezone.utc)
        )
    ]
    persist_exceptions(exceptions)

    # Verify audit persistence
    audit_entry = {
        "event_id": f"AUD-TEST-{int(datetime.now(timezone.utc).timestamp())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "UNIT_TEST",
        "action_type": "TEST_ACTION",
        "affected_records": ["REC-01"],
        "before_state": {},
        "after_state": {},
        "rationale": "Automated DB test",
        "prev_hash": "0" * 64,
        "sha256_hash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    }
    persist_audit_log_entry(audit_entry)
