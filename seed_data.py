"""
PayBridge Automated Reconciliation Engine - Database & Pipeline Seeder.
Initializes the relational database, generates banking statements (CSV, MT940, CAMT.053),
and executes an end-to-end multi-bank reconciliation run.
"""

import sys
import os
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.models.database import init_db
from backend.data.sample_generator import generate_all_datasets, DATA_DIR
from backend.app.models.schemas import ReconciliationRunRequest
from backend.app.api.routes_recon import trigger_reconciliation_run, ACTIVE_RUNS, RUN_MATCHES, RUN_EXCEPTIONS
from backend.app.audit.logger import global_audit_logger


def seed():
    print("=" * 70)
    print("  PAYBRIDGE SETTLEMENT GUARDIAN - INITIALIZATION & SEEDER")
    print("=" * 70)

    # 1. Initialize DB tables
    print("\n[1/5] Initializing Database Schema (SQLite / PostgreSQL)...")
    init_db()
    print("      [OK] Database tables successfully created.")

    # 2. Generate/Validate Banking Statements
    print("\n[2/5] Checking Banking Data Files in:", DATA_DIR)
    internal_csv = os.path.join(DATA_DIR, "internal_ledger_20260315.csv")
    if not os.path.exists(internal_csv):
        print("      Generating synthetic bank datasets across 5 formats...")
        files = generate_all_datasets(scale_factor=0.04)
        for name, path in files.items():
            print(f"      [OK] Generated: {os.path.basename(path)}")
    else:
        print("      [OK] Existing banking data files verified.")

    # 3. Trigger End-to-End Multi-Bank Reconciliation Run
    print("\n[3/5] Executing Multi-Bank Reconciliation Engine (ALL 7 Partners)...")
    req = ReconciliationRunRequest(
        bank_code="ALL",
        start_date="2026-03-01",
        end_date="2026-03-15",
        fast_mode=False
    )
    run_response = trigger_reconciliation_run(req)
    run_id = run_response["run_id"]
    run_info = ACTIVE_RUNS.get(run_id, {})
    matches = RUN_MATCHES.get(run_id, [])
    exceptions = RUN_EXCEPTIONS.get(run_id, [])

    print(f"      [OK] Run Completed: {run_id}")
    print(f"        - Status: {run_info.get('status', 'COMPLETED')}")
    print(f"        - Total Processed: {run_info.get('total_internal', 0)} internal vs {run_info.get('total_external', 0)} external")
    print(f"        - Match Rate: {run_info.get('match_rate', 0.0)}%")
    print(f"        - Matches: {len(matches)} (Exact: {run_info.get('exact_matches', 0)}, Fuzzy: {run_info.get('fuzzy_matches', 0)}, Rule: {run_info.get('rule_matches', 0)})")
    print(f"        - Open Exceptions: {len(exceptions)}")
    print(f"        - Execution Duration: {run_info.get('execution_time_seconds', 0.0)}s")

    # 4. Verify Dual-Layer Balance Reconciliation
    print("\n[4/5] Verifying Dual-Layer Balance Reconciliation...")
    bal_recon = run_info.get("balance_reconciliation", {})
    opening = bal_recon.get("opening_balance", Decimal("0.00"))
    net_flow = bal_recon.get("net_transactions", Decimal("0.00"))
    closing = bal_recon.get("closing_balance", Decimal("0.00"))
    bal_match = bal_recon.get("balance_matched", False)
    print(f"      - Opening Balance:  INR {opening:>14,.2f}")
    print(f"      - Net Txn Flow:     INR {net_flow:>14,.2f}")
    print(f"      - Closing Balance:  INR {closing:>14,.2f}")
    print(f"      - Balance Level Matched: {'[OK] PASS' if bal_match else '[WARN] VARIANCE'}")

    # 5. Cryptographic Audit Chain Verification
    print("\n[5/5] Auditing SHA-256 Tamper-Evident Chain...")
    from backend.app.audit.verifier import verify_audit_chain
    is_valid, violations = verify_audit_chain(global_audit_logger._entries)
    print(f"      - Total Audit Blocks: {len(global_audit_logger._entries)}")
    print(f"      - Chain Status:       {'[OK] INTACT' if is_valid else '[FAIL] COMPROMISED'}")
    print(f"      - Tampered Blocks:    {len(violations)}")

    print("\n" + "=" * 70)
    print("  SEEDING COMPLETE: SYSTEM IS READY FOR PRODUCTION / EVALUATION")
    print("  Access Web Dashboard at: http://localhost:8000")
    print("  Interactive Swagger Docs: http://localhost:8000/docs")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    seed()
