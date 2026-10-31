"""
Reconciliation Run Execution and Result API Routes.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query
import yaml

from backend.app.models.schemas import (
    ReconciliationRunRequest, MatchResultItem, ExceptionItem,
    RunStatusEnum, DashboardSummaryResponse
)
from backend.app.models.canonical import CanonicalTransaction, SourceFormatEnum
from backend.app.models.db_service import (
    persist_reconciliation_run, persist_match_results,
    persist_exceptions, load_all_runs_from_db
)
from backend.app.parsers.csv_parser import CSVParser
from backend.app.parsers.mt940_parser import MT940Parser
from backend.app.parsers.camt053_parser import CAMT053Parser
from backend.app.parsers.detector import detect_file_format
from backend.app.matching.engine import MatchingOrchestrator
from backend.app.exceptions.classifier import ExceptionClassifier
from backend.app.exceptions.escalation import EscalationManager
from backend.app.exceptions.resolver import ExceptionResolver
from backend.app.audit.logger import global_audit_logger
from backend.app.anomaly.detector import AnomalyDetector
from backend.data.sample_generator import generate_all_datasets, DATA_DIR

router = APIRouter(prefix="/api/v1/reconciliation", tags=["Reconciliation"])

# In-memory storage for active runs, matches, and exceptions
ACTIVE_RUNS: Dict[str, Dict[str, Any]] = {}
RUN_MATCHES: Dict[str, List[MatchResultItem]] = {}
RUN_EXCEPTIONS: Dict[str, List[ExceptionItem]] = {}
ACTIVE_ANOMALIES: List[Dict[str, Any]] = []


def _load_bank_config(bank_code: str) -> Dict[str, Any]:
    config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
    cfg_file = os.path.join(config_dir, f"{bank_code.lower()}_config.yaml")
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {"bank_code": bank_code, "timezone": "Asia/Kolkata", "currency": "INR"}


@router.post("/run")
def trigger_reconciliation_run(req: ReconciliationRunRequest):
    """
    Triggers an automated multi-bank reconciliation run.
    Parses bank statements, normalises to canonical schema, executes 3-tier matching,
    classifies exceptions, evaluates SLAs, and logs to cryptographic audit chain.
    """
    # Ensure sample datasets exist
    if not os.path.exists(os.path.join(DATA_DIR, "internal_ledger_20260315.csv")):
        generate_all_datasets(scale_factor=0.04)

    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # Log Run Start Event to Cryptographic Audit
    global_audit_logger.log_event(
        actor="SYSTEM_SCHEDULER",
        action_type="RUN_START",
        affected_records=[run_id],
        rationale=f"Initiated reconciliation run for bank {req.bank_code} (Fast Mode: {req.fast_mode})"
    )

    # 1. Parse Internal Ledger (Source of Truth)
    internal_csv_path = os.path.join(DATA_DIR, "internal_ledger_20260315.csv")
    csv_parser = CSVParser()
    with open(internal_csv_path, "r", encoding="utf-8") as f:
        internal_content = f.read()
    
    int_config = {
        "column_mappings": {
            "txn_id": "transaction_id",
            "txn_date": "transaction_date",
            "amount": "net_amount",
            "currency": "currency",
            "direction": "cr_dr",
            "counterparty_name": "merchant_name",
            "counterparty_account": "account_number",
            "bank_ref": "bank_ref_no",
            "narration": "remarks",
            "settlement_date": "settlement_date"
        }
    }
    int_parse_res = csv_parser.parse_content(internal_content, "internal_ledger_20260315.csv", "INTERNAL", int_config)
    internal_txns = int_parse_res.transactions

    # 2. Parse Target Bank Statement Files
    external_txns: List[CanonicalTransaction] = []
    all_parse_errors = []
    bank_code_upper = req.bank_code.upper()

    banks_to_process = ["HDFC", "ICICI", "AXIS", "SBI", "KOTAK"] if bank_code_upper in ("ALL", "7_PARTNERS") else [bank_code_upper]

    opening_bal = Decimal("0.00")
    closing_bal = Decimal("0.00")

    for b in banks_to_process:
        b_cfg = _load_bank_config(b)

        if b == "HDFC":
            path = os.path.join(DATA_DIR, "hdfc_settlement_20260315.csv")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    res = csv_parser.parse_content(f.read(), "hdfc_settlement_20260315.csv", "HDFC", b_cfg)
                    external_txns.extend(res.transactions)
                    all_parse_errors.extend(res.parse_errors)

        elif b == "ICICI":
            path = os.path.join(DATA_DIR, "icici_settlement_20260315.csv")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    res = csv_parser.parse_content(f.read(), "icici_settlement_20260315.csv", "ICICI", b_cfg)
                    external_txns.extend(res.transactions)
                    all_parse_errors.extend(res.parse_errors)

        elif b == "AXIS":
            path = os.path.join(DATA_DIR, "axis_mt940_20260315.sta")
            if os.path.exists(path):
                mt_parser = MT940Parser()
                with open(path, "r", encoding="utf-8") as f:
                    res = mt_parser.parse_content(f.read(), "axis_mt940_20260315.sta", "AXIS", b_cfg)
                    external_txns.extend(res.transactions)
                    all_parse_errors.extend(res.parse_errors)
                    if res.balances and res.balances.opening_balance is not None:
                        opening_bal += res.balances.opening_balance
                        closing_bal += res.balances.closing_balance or Decimal("0.00")

        elif b == "SBI":
            path = os.path.join(DATA_DIR, "sbi_mt940_20260315.sta")
            if os.path.exists(path):
                mt_parser = MT940Parser()
                with open(path, "r", encoding="utf-8") as f:
                    res = mt_parser.parse_content(f.read(), "sbi_mt940_20260315.sta", "SBI", b_cfg)
                    external_txns.extend(res.transactions)
                    all_parse_errors.extend(res.parse_errors)

        elif b == "KOTAK":
            path = os.path.join(DATA_DIR, "kotak_camt053_20260315.xml")
            if os.path.exists(path):
                camt_parser = CAMT053Parser()
                with open(path, "r", encoding="utf-8") as f:
                    res = camt_parser.parse_content(f.read(), "kotak_camt053_20260315.xml", "KOTAK", b_cfg)
                    external_txns.extend(res.transactions)
                    all_parse_errors.extend(res.parse_errors)

    # 3. Anomaly Detection
    anomaly_detector = AnomalyDetector()
    detected_anomalies = anomaly_detector.detect_anomalies(external_txns, bank_code=req.bank_code)
    global ACTIVE_ANOMALIES
    ACTIVE_ANOMALIES = detected_anomalies

    # 4. Matching Orchestration
    orchestrator = MatchingOrchestrator(
        tolerance_amount=req.tolerance_amount,
        tolerance_fx=req.tolerance_fx,
        fast_mode=req.fast_mode
    )
    matches, rem_int, rem_ext, metrics = orchestrator.execute(
        internal_records=internal_txns,
        external_records=external_txns,
        run_id=run_id
    )

    # Log Matching Event to Audit
    global_audit_logger.log_event(
        actor="MATCHING_ENGINE",
        action_type="MATCH_EXECUTION",
        affected_records=[m.match_id for m in matches[:10]],
        rationale=f"Resolved {len(matches)} matched pairs across 3 stages (Exact: {metrics['exact_matches']}, Fuzzy: {metrics['fuzzy_matches']}, Rule: {metrics['rule_matches']})"
    )

    # 5. Exception Classification
    classifier = ExceptionClassifier()
    exceptions = classifier.classify_exceptions(
        unmatched_internal=rem_int,
        unmatched_external=rem_ext,
        parse_errors=all_parse_errors,
        run_id=run_id
    )

    # 6. Auto-Resolution for Tier 1
    resolver = ExceptionResolver()
    exceptions, new_auto_matches, auto_resolved_count = resolver.auto_resolve_tier1(exceptions, run_id=run_id)
    matches.extend(new_auto_matches)

    # 7. Escalation & SLA Evaluation
    escalation_mgr = EscalationManager()
    exceptions, esc_metrics = escalation_mgr.check_sla_and_escalate(exceptions)

    # 8. Dual-Layer Balance Validation
    net_transactions = sum(Decimal(t.amount) if t.direction.value == "CR" else -Decimal(t.amount) for t in external_txns)
    computed_closing = opening_bal + net_transactions
    balance_reconciled = (opening_bal == Decimal("0.00")) or abs(computed_closing - closing_bal) <= Decimal("1000.00")

    run_record = {
        "run_id": run_id,
        "bank_code": req.bank_code,
        "status": RunStatusEnum.COMPLETED.value,
        "fast_mode": req.fast_mode,
        "total_internal": len(internal_txns),
        "total_external": len(external_txns),
        "matched_count": len(matches),
        "exact_matches": metrics["exact_matches"],
        "fuzzy_matches": metrics["fuzzy_matches"],
        "rule_matches": metrics["rule_matches"],
        "split_matches": metrics["split_matches"],
        "netted_matches": metrics["netted_matches"],
        "exception_count": len(exceptions),
        "auto_resolved_count": auto_resolved_count,
        "match_rate": metrics["match_rate"],
        "duration_ms": metrics["duration_ms"],
        "opening_balance": str(opening_bal),
        "closing_balance": str(closing_bal),
        "computed_closing_balance": str(computed_closing),
        "balance_reconciled": balance_reconciled,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "stages": metrics["stages"]
    }

    ACTIVE_RUNS[run_id] = run_record
    RUN_MATCHES[run_id] = matches
    RUN_EXCEPTIONS[run_id] = exceptions

    # Persist to Relational Database (Section A6.2 & Section 128 Companies Act)
    try:
        persist_reconciliation_run(run_record)
        persist_match_results(matches)
        persist_exceptions(exceptions)
    except Exception as e:
        print(f"[DB Warning] Could not persist run to DB: {e}")

    # Final Audit Log Entry
    global_audit_logger.log_event(
        actor="SYSTEM_ORCHESTRATOR",
        action_type="RUN_COMPLETE",
        affected_records=[run_id],
        rationale=f"Completed run with match rate {metrics['match_rate']}%, {len(exceptions)} exceptions, {auto_resolved_count} auto-resolved."
    )

    return {
        "status": "SUCCESS",
        "run_id": run_id,
        "summary": run_record,
        "anomalies_count": len(detected_anomalies),
        "anomalies": detected_anomalies
    }


@router.get("/runs")
def list_reconciliation_runs():
    """Returns list of all reconciliation runs (persisted in DB or memory)."""
    if not ACTIVE_RUNS:
        try:
            db_runs = load_all_runs_from_db()
            if db_runs:
                return db_runs
        except Exception:
            pass
    return list(ACTIVE_RUNS.values())


@router.get("/runs/{run_id}")
def get_run_details(run_id: str):
    """Get status and metrics for a specific run."""
    if run_id not in ACTIVE_RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    return ACTIVE_RUNS[run_id]


@router.get("/runs/{run_id}/results")
def get_run_results(
    run_id: str,
    match_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get paginated match results for a specific run."""
    if run_id not in RUN_MATCHES:
        raise HTTPException(status_code=404, detail="No match results found for run")
    matches = RUN_MATCHES[run_id]
    if match_type:
        matches = [m for m in matches if m.match_type.value.upper() == match_type.upper()]
    return {
        "total": len(matches),
        "limit": limit,
        "offset": offset,
        "results": matches[offset:offset+limit]
    }
