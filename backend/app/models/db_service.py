"""
Database Persistence Service for Reconciliation Engine.
Handles transactional persistence and queries for runs, transactions, matches, exceptions, and audit logs.
Fulfills Companies Act 2013 (Section 128) and RBI Master Direction audit persistence requirements.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from backend.app.models.database import (
    SessionLocal, ReconciliationRun, MatchResult,
    ReconciliationException, AuditLog, NormalisedTransaction, RawTransaction
)
from backend.app.models.canonical import CanonicalTransaction
from backend.app.models.schemas import MatchResultItem, ExceptionItem, AuditLogItem


def get_db_session() -> Session:
    return SessionLocal()


def persist_reconciliation_run(run_data: Dict[str, Any]) -> None:
    """Saves or updates a ReconciliationRun in the database."""
    session = get_db_session()
    try:
        run_id = run_data["run_id"]
        db_run = session.query(ReconciliationRun).filter_by(run_id=run_id).first()
        if not db_run:
            db_run = ReconciliationRun(
                run_id=run_id,
                bank_code=run_data.get("bank_code", "ALL"),
                status=run_data.get("status", "COMPLETED"),
                fast_mode=run_data.get("fast_mode", False),
                total_internal=run_data.get("total_internal", 0),
                total_external=run_data.get("total_external", 0),
                matched_count=run_data.get("matched_count", 0),
                exact_matches=run_data.get("exact_matches", 0),
                fuzzy_matches=run_data.get("fuzzy_matches", 0),
                rule_matches=run_data.get("rule_matches", 0),
                split_matches=run_data.get("split_matches", 0),
                netted_matches=run_data.get("netted_matches", 0),
                exception_count=run_data.get("exception_count", 0),
                auto_resolved_count=run_data.get("auto_resolved_count", 0),
                match_rate=run_data.get("match_rate", 0.0),
                duration_ms=run_data.get("duration_ms", 0.0),
                opening_balance=str(run_data.get("opening_balance", "0.00")),
                closing_balance=str(run_data.get("closing_balance", "0.00")),
                computed_closing_balance=str(run_data.get("computed_closing_balance", "0.00")),
                balance_reconciled=run_data.get("balance_reconciled", True),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc)
            )
            session.add(db_run)
        else:
            db_run.status = run_data.get("status", db_run.status)
            db_run.matched_count = run_data.get("matched_count", db_run.matched_count)
            db_run.exception_count = run_data.get("exception_count", db_run.exception_count)
            db_run.auto_resolved_count = run_data.get("auto_resolved_count", db_run.auto_resolved_count)
            db_run.match_rate = run_data.get("match_rate", db_run.match_rate)
            db_run.completed_at = datetime.now(timezone.utc)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def persist_match_results(matches: List[MatchResultItem]) -> None:
    """Batch-persists matched transaction pairs."""
    if not matches:
        return
    session = get_db_session()
    try:
        db_items = []
        for m in matches:
            # Check if exists
            exists = session.query(MatchResult).filter_by(match_id=m.match_id).first()
            if not exists:
                db_m = MatchResult(
                    match_id=m.match_id,
                    run_id=m.run_id,
                    internal_txn_id=m.internal_txn_id,
                    external_txn_id=m.external_txn_id,
                    internal_txn_ids_json=m.internal_txn_ids,
                    external_txn_ids_json=m.external_txn_ids,
                    match_type=m.match_type.value,
                    confidence_score=m.confidence_score,
                    rule_name=m.rule_name,
                    internal_amount=m.internal_amount,
                    external_amount=m.external_amount,
                    amount_diff=m.amount_diff or "0.00",
                    bank_code=m.bank_code,
                    breakdown_json=m.breakdown or {},
                    matched_at=m.matched_at or datetime.now(timezone.utc)
                )
                db_items.append(db_m)

        if db_items:
            session.bulk_save_objects(db_items)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def persist_exceptions(exceptions: List[ExceptionItem]) -> None:
    """Persists or updates exception records in the database."""
    if not exceptions:
        return
    session = get_db_session()
    try:
        for exc in exceptions:
            db_exc = session.query(ReconciliationException).filter_by(exception_id=exc.exception_id).first()
            if not db_exc:
                db_exc = ReconciliationException(
                    exception_id=exc.exception_id,
                    run_id=exc.run_id,
                    category=exc.category.value,
                    severity=exc.severity.value,
                    status=exc.status.value,
                    assigned_tier=exc.assigned_tier.value,
                    bank_code=exc.bank_code,
                    internal_txn_id=exc.internal_txn_id,
                    external_txn_id=exc.external_txn_id,
                    affected_amount=exc.affected_amount,
                    currency=exc.currency,
                    description=exc.description,
                    suggested_resolution=exc.suggested_resolution,
                    resolution_action=exc.resolution_notes,
                    resolution_notes=exc.resolution_notes,
                    resolved_by=exc.resolved_by,
                    resolved_at=exc.resolved_at,
                    sla_minutes=exc.sla_minutes,
                    created_at=exc.created_at or datetime.now(timezone.utc),
                    sla_deadline=exc.sla_deadline,
                    auto_resolvable=exc.auto_resolvable
                )
                session.add(db_exc)
            else:
                db_exc.status = exc.status.value
                db_exc.resolution_action = exc.resolution_notes
                db_exc.resolution_notes = exc.resolution_notes
                db_exc.resolved_by = exc.resolved_by
                db_exc.resolved_at = exc.resolved_at

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def persist_audit_log_entry(entry_dict: Dict[str, Any]) -> None:
    """Persists an immutable audit log entry."""
    session = get_db_session()
    try:
        db_log = AuditLog(
            event_id=entry_dict["event_id"],
            timestamp=datetime.fromisoformat(entry_dict["timestamp"]) if isinstance(entry_dict["timestamp"], str) else entry_dict["timestamp"],
            actor=entry_dict["actor"],
            action_type=entry_dict["action_type"],
            affected_records=entry_dict.get("affected_records", []),
            before_state=entry_dict.get("before_state"),
            after_state=entry_dict.get("after_state"),
            rationale=entry_dict.get("rationale", ""),
            prev_hash=entry_dict["prev_hash"],
            sha256_hash=entry_dict["sha256_hash"]
        )
        session.add(db_log)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def load_all_runs_from_db() -> List[Dict[str, Any]]:
    """Loads all reconciliation runs from the database."""
    session = get_db_session()
    try:
        runs = session.query(ReconciliationRun).order_by(ReconciliationRun.started_at.desc()).all()
        result = []
        for r in runs:
            result.append({
                "run_id": r.run_id,
                "bank_code": r.bank_code,
                "status": r.status,
                "fast_mode": r.fast_mode,
                "total_internal": r.total_internal,
                "total_external": r.total_external,
                "matched_count": r.matched_count,
                "exact_matches": r.exact_matches,
                "fuzzy_matches": r.fuzzy_matches,
                "rule_matches": r.rule_matches,
                "split_matches": r.split_matches,
                "netted_matches": r.netted_matches,
                "exception_count": r.exception_count,
                "auto_resolved_count": r.auto_resolved_count,
                "match_rate": r.match_rate,
                "duration_ms": r.duration_ms,
                "opening_balance": r.opening_balance,
                "closing_balance": r.closing_balance,
                "computed_closing_balance": r.computed_closing_balance,
                "balance_reconciled": r.balance_reconciled,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            })
        return result
    finally:
        session.close()
