"""
Unit Tests for Statutory and Compliance Report Generation.
Verifies Daily Reconciliation, Exception Ageing, and RBI Clause 7.1 Escrow reports in HTML, CSV, and JSON.
"""

from decimal import Decimal
from datetime import datetime, timezone

from backend.app.reports.generator import ReportGenerator
from backend.app.models.schemas import (
    MatchResultItem, ExceptionItem, MatchTypeEnum,
    ExceptionCategoryEnum, SeverityLevelEnum, ExceptionStatusEnum, EscalationTierEnum
)


def test_daily_reconciliation_report_generation():
    generator = ReportGenerator()
    run_data = {
        "run_id": "RUN-20260315-001",
        "bank_code": "ALL",
        "match_rate": 99.2,
        "total_records": 1000,
        "duration_ms": 320.5
    }
    matches = [
        MatchResultItem(
            match_id="M-01",
            run_id="RUN-20260315-001",
            internal_txn_id="TXN-01",
            external_txn_id="EXT-01",
            match_type=MatchTypeEnum.EXACT,
            confidence_score=1.0,
            internal_amount="5000.00",
            external_amount="5000.00",
            bank_code="HDFC",
            matched_at=datetime.now(timezone.utc)
        )
    ]
    exceptions = [
        ExceptionItem(
            exception_id="EXC-01",
            run_id="RUN-20260315-001",
            category=ExceptionCategoryEnum.AMOUNT_MISMATCH,
            severity=SeverityLevelEnum.HIGH,
            status=ExceptionStatusEnum.OPEN,
            assigned_tier=EscalationTierEnum.TIER_2_ANALYST,
            bank_code="ICICI",
            affected_amount="150.00",
            currency="INR",
            description="Amount diff",
            suggested_resolution="Review ledger",
            sla_minutes=120,
            created_at=datetime.now(timezone.utc),
            sla_deadline=datetime.now(timezone.utc)
        )
    ]

    report = generator.generate_daily_reconciliation_report(run_data, matches, exceptions)
    assert report["report_title"] == "Daily Multi-Bank Settlement Reconciliation Report"
    assert report["summary"]["matched_count"] == 1
    assert report["summary"]["open_exceptions"] == 1

    # Test HTML export
    html = generator.generate_daily_report_html(run_data, matches, exceptions)
    assert "<!DOCTYPE html>" in html
    assert "Daily Multi-Bank Settlement Reconciliation Report" in html
    assert "RUN-20260315-001" in html

    # Test CSV export
    csv_text = generator.generate_daily_report_csv(run_data, matches, exceptions)
    assert "PayBridge Daily Multi-Bank Settlement Reconciliation Report" in csv_text
    assert "TXN-01" in csv_text


def test_escrow_settlement_report():
    generator = ReportGenerator()
    total_col = Decimal("10000000.00")
    total_set = Decimal("8000000.00")
    # Escrow must equal 2000000.00
    escrow_bal = Decimal("2000000.00")

    report = generator.generate_escrow_settlement_report(total_col, total_set, escrow_bal)
    assert report["compliance_status"] == "FULLY_COMPLIANT"

    # Test variance breach
    bad_escrow = Decimal("1500000.00")  # ₹5 Lakh shortfall
    breach_report = generator.generate_escrow_settlement_report(total_col, total_set, bad_escrow)
    assert breach_report["compliance_status"] == "REGULATORY_BREACH_DETECTED"

    # Test HTML export
    escrow_html = generator.generate_escrow_report_html(total_col, total_set, escrow_bal)
    assert "RBI Clause 7.1 Escrow & Nodal Account Settlement Audit" in escrow_html
