"""
Comprehensive Unit Tests for 18-Category Exception Classification, SLAs, and Escalation Tiers.
"""

from decimal import Decimal
from datetime import datetime, timezone, timedelta

from backend.app.models.canonical import CanonicalTransaction, DirectionEnum
from backend.app.exceptions.classifier import ExceptionClassifier
from backend.app.exceptions.resolver import ExceptionResolver
from backend.app.exceptions.escalation import EscalationManager
from backend.app.models.schemas import (
    ExceptionCategoryEnum, SeverityLevelEnum, EscalationTierEnum, ExceptionStatusEnum
)


def test_exception_direction_reversal_corrected_sla():
    """Test that DIRECTION_REVERSAL has 30 minute SLA and Tier 4 Compliance escalation."""
    classifier = ExceptionClassifier()
    int_txn = CanonicalTransaction(
        txn_id="TXN-REV-01",
        txn_date=datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("50000.00"),
        currency="INR",
        direction=DirectionEnum.CR,
        counterparty_name="TATA DIGITAL"
    )
    ext_txn = CanonicalTransaction(
        txn_id="TXN-REV-01",
        txn_date=datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("50000.00"),
        currency="INR",
        direction=DirectionEnum.DR,  # Reversed!
        counterparty_name="TATA DIGITAL"
    )

    exceptions = classifier.classify_exceptions(
        unmatched_internal=[int_txn],
        unmatched_external=[ext_txn],
        parse_errors=[],
        run_id="RUN-TEST"
    )

    assert len(exceptions) == 1
    exc = exceptions[0]
    assert exc.category == ExceptionCategoryEnum.DIRECTION_REVERSAL
    assert exc.sla_minutes == 30
    assert exc.assigned_tier == EscalationTierEnum.TIER_4_COMPLIANCE


def test_exception_reference_truncated():
    """Test classification and auto-resolution for truncated bank reference numbers."""
    classifier = ExceptionClassifier()
    resolver = ExceptionResolver()

    # Bank truncated reference to 16 chars
    full_ref = "HDFC2026031599988877"
    truncated_ref = "HDFC202603159998"

    int_txn = CanonicalTransaction(
        txn_id=full_ref,
        txn_date=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("12500.00"),
        currency="INR",
        direction=DirectionEnum.CR,
        counterparty_name="RELIANCE RETAIL"
    )
    ext_txn = CanonicalTransaction(
        txn_id=truncated_ref,
        txn_date=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("12500.00"),
        currency="INR",
        direction=DirectionEnum.CR,
        counterparty_name="RELIANCE RETAIL"
    )

    exceptions = classifier.classify_exceptions(
        unmatched_internal=[int_txn],
        unmatched_external=[ext_txn],
        parse_errors=[],
        run_id="RUN-TEST-TRUNC"
    )

    assert len(exceptions) == 1
    assert exceptions[0].category == ExceptionCategoryEnum.REFERENCE_TRUNCATED
    assert exceptions[0].auto_resolvable is True

    # Test Tier 1 Auto-Resolution
    resolved_excs, new_matches, count = resolver.auto_resolve_tier1(exceptions, "RUN-TEST-TRUNC")
    assert count == 1
    assert resolved_excs[0].status == ExceptionStatusEnum.AUTO_RESOLVED
    assert resolved_excs[0].resolution_action == "PREFIX_REFERENCE_MATCHED"


def test_exception_regulatory_hold():
    """Test classification of transactions flagged for AML / CFT / Compliance hold."""
    classifier = ExceptionClassifier()
    int_txn = CanonicalTransaction(
        txn_id="TXN-AML-001",
        txn_date=datetime(2026, 3, 15, 14, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("8500000.00"),
        currency="INR",
        direction=DirectionEnum.CR,
        narration="SUSPECTED AML PATTERN HIGH VELOCITY HOLD"
    )
    ext_txn = CanonicalTransaction(
        txn_id="TXN-AML-001",
        txn_date=datetime(2026, 3, 15, 14, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("8500000.00"),
        currency="INR",
        direction=DirectionEnum.CR,
        narration="SUSPECTED AML PATTERN HIGH VELOCITY HOLD"
    )

    exceptions = classifier.classify_exceptions(
        unmatched_internal=[int_txn],
        unmatched_external=[ext_txn],
        parse_errors=[],
        run_id="RUN-TEST-AML"
    )

    assert len(exceptions) == 1
    assert exceptions[0].category == ExceptionCategoryEnum.REGULATORY_HOLD
    assert exceptions[0].severity == SeverityLevelEnum.CRITICAL
    assert exceptions[0].assigned_tier == EscalationTierEnum.TIER_4_COMPLIANCE


def test_exception_duplicate_internal():
    """Test duplicate internal entry detection and auto-voiding."""
    classifier = ExceptionClassifier()
    resolver = ExceptionResolver()

    txn1 = CanonicalTransaction(
        txn_id="TXN-DUP-01",
        txn_date=datetime(2026, 3, 15, 9, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("5000.00"),
        currency="INR",
        direction=DirectionEnum.CR
    )
    txn2 = CanonicalTransaction(
        txn_id="TXN-DUP-01",
        txn_date=datetime(2026, 3, 15, 9, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("5000.00"),
        currency="INR",
        direction=DirectionEnum.CR
    )

    exceptions = classifier.classify_exceptions(
        unmatched_internal=[txn1, txn2],
        unmatched_external=[],
        parse_errors=[],
        run_id="RUN-TEST-DUP"
    )

    dup_excs = [e for e in exceptions if e.category == ExceptionCategoryEnum.DUPLICATE_INTERNAL]
    assert len(dup_excs) == 1
    assert dup_excs[0].auto_resolvable is True

    resolved_excs, _, count = resolver.auto_resolve_tier1(dup_excs, "RUN-TEST-DUP")
    assert count == 1
    assert resolved_excs[0].status == ExceptionStatusEnum.AUTO_RESOLVED


def test_exception_fee_deduction():
    """Test bank fee deduction identification and auto-adjustment."""
    classifier = ExceptionClassifier()
    resolver = ExceptionResolver()

    int_txn = CanonicalTransaction(
        txn_id="TXN-FEE-01",
        txn_date=datetime(2026, 3, 15, 11, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("1000.00"),
        currency="INR",
        direction=DirectionEnum.CR
    )
    ext_txn = CanonicalTransaction(
        txn_id="TXN-FEE-01",
        txn_date=datetime(2026, 3, 15, 11, 0, 0, tzinfo=timezone.utc),
        amount=Decimal("985.00"),  # Bank deducted ₹15 fee
        currency="INR",
        direction=DirectionEnum.CR,
        narration="SETTLEMENT NET OF MDR FEE"
    )

    exceptions = classifier.classify_exceptions(
        unmatched_internal=[int_txn],
        unmatched_external=[ext_txn],
        parse_errors=[],
        run_id="RUN-TEST-FEE"
    )

    assert len(exceptions) == 1
    assert exceptions[0].category == ExceptionCategoryEnum.FEE_DEDUCTION
    assert exceptions[0].auto_resolvable is True


def test_escalation_manager_sla_breach_and_tier_escalation():
    """Test SLA monitoring and automatic escalation to Tier 3 on SLA breach."""
    mgr = EscalationManager()
    base_time = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)

    # Item with deadline in the past
    exc = classifier = ExceptionClassifier().classify_exceptions(
        unmatched_internal=[],
        unmatched_external=[],
        parse_errors=[{"bank_code": "HDFC", "error": "Invalid syntax"}],
        run_id="RUN-TEST-ESC"
    )[0]

    # Advance time past SLA deadline
    future_time = base_time + timedelta(hours=3)
    exc.sla_deadline = base_time + timedelta(hours=1)

    escalated_list, metrics = mgr.check_sla_and_escalate([exc], current_time=future_time)
    assert escalated_list[0].is_sla_breached is True
    assert escalated_list[0].status == ExceptionStatusEnum.ESCALATED
    assert metrics["sla_breached_count"] == 1
