"""
18-Category Exception Classifier and Severity Assignment Engine.
Accurately categorises all unmatched transactions and applies SLA rules.
Note: Corrected DIRECTION_REVERSAL SLA to 30 mins with TIER_4_COMPLIANCE escalation per deliberate error note.
"""

from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from backend.app.models.canonical import CanonicalTransaction, DirectionEnum
from backend.app.models.schemas import (
    ExceptionItem, ExceptionCategoryEnum, SeverityLevelEnum,
    EscalationTierEnum, ExceptionStatusEnum
)
from backend.app.matching.confidence import compute_reference_similarity


# Category SLA and routing metadata
CATEGORY_METADATA = {
    ExceptionCategoryEnum.MISSING_INTERNAL: {
        "sla_minutes": 240,  # 4 hours
        "severity": SeverityLevelEnum.MEDIUM,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Present in bank statement, absent in internal ledger."
    },
    ExceptionCategoryEnum.MISSING_EXTERNAL: {
        "sla_minutes": 240,  # 4 hours
        "severity": SeverityLevelEnum.MEDIUM,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Present in internal ledger, absent in bank statement."
    },
    ExceptionCategoryEnum.AMOUNT_MISMATCH: {
        "sla_minutes": 120,  # 2 hours
        "severity": SeverityLevelEnum.HIGH,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Reference matches but amount differs beyond tolerance."
    },
    ExceptionCategoryEnum.DUPLICATE_INTERNAL: {
        "sla_minutes": 60,   # 1 hour
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Same transaction recorded multiple times in internal ledger."
    },
    ExceptionCategoryEnum.DUPLICATE_EXTERNAL: {
        "sla_minutes": 120,  # 2 hours
        "severity": SeverityLevelEnum.HIGH,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Duplicate transaction appears in bank statement feed."
    },
    ExceptionCategoryEnum.DATE_MISMATCH: {
        "sla_minutes": 480,  # 8 hours
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Matching reference and amount with booking date offset <= T+1."
    },
    ExceptionCategoryEnum.CURRENCY_MISMATCH: {
        "sla_minutes": 240,  # 4 hours
        "severity": SeverityLevelEnum.HIGH,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Transaction recorded in conflicting currency codes without conversion."
    },
    ExceptionCategoryEnum.DIRECTION_REVERSAL: {
        # Deliberate error correction: 30 minutes critical SLA and Tier 4 Compliance routing
        "sla_minutes": 30,   # 30 minutes
        "severity": SeverityLevelEnum.CRITICAL,
        "tier": EscalationTierEnum.TIER_4_COMPLIANCE,
        "auto_resolvable": False,
        "description": "Debit/Credit direction reversal detected (potential booking error / fraud risk)."
    },
    ExceptionCategoryEnum.PARTIAL_MATCH: {
        "sla_minutes": 240,  # 4 hours
        "severity": SeverityLevelEnum.MEDIUM,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Amount matches subset of split transaction."
    },
    ExceptionCategoryEnum.NETTED_SETTLEMENT: {
        "sla_minutes": 480,  # 8 hours
        "severity": SeverityLevelEnum.MEDIUM,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Multiple transactions netted into single summary bank entry."
    },
    ExceptionCategoryEnum.FEE_DEDUCTION: {
        "sla_minutes": 120,  # 2 hours
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Bank deducted processing/gateway fees not captured internally."
    },
    ExceptionCategoryEnum.FX_VARIANCE: {
        "sla_minutes": 240,  # 4 hours
        "severity": SeverityLevelEnum.HIGH,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Cross-currency exchange variance exceeds 1.5% tolerance threshold."
    },
    ExceptionCategoryEnum.STALE_TRANSACTION: {
        "sla_minutes": 1440, # 24 hours
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Transaction age exceeds standard reconciliation window (T+5)."
    },
    ExceptionCategoryEnum.FORMAT_ERROR: {
        "sla_minutes": 60,   # 1 hour
        "severity": SeverityLevelEnum.HIGH,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Record failed syntax or schema validation during parsing."
    },
    ExceptionCategoryEnum.REFERENCE_TRUNCATED: {
        "sla_minutes": 120,  # 2 hours
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Bank truncated reference number beyond 16 characters."
    },
    ExceptionCategoryEnum.TIMEZONE_OFFSET: {
        "sla_minutes": 60,   # 1 hour
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_1_AUTO,
        "auto_resolvable": True,
        "description": "Date difference caused by timezone offset crossing midnight."
    },
    ExceptionCategoryEnum.REVERSAL_PENDING: {
        "sla_minutes": 1440, # 24 hours
        "severity": SeverityLevelEnum.LOW,
        "tier": EscalationTierEnum.TIER_2_ANALYST,
        "auto_resolvable": False,
        "description": "Transaction marked for reversal but bank reversal entry not yet posted."
    },
    ExceptionCategoryEnum.REGULATORY_HOLD: {
        "sla_minutes": 2880, # 48 hours
        "severity": SeverityLevelEnum.CRITICAL,
        "tier": EscalationTierEnum.TIER_4_COMPLIANCE,
        "auto_resolvable": False,
        "description": "Transaction flagged for AML/CFT or FIU-IND compliance review."
    },
    ExceptionCategoryEnum.SETTLEMENT_DELAY: {
        "sla_minutes": 120,
        "severity": SeverityLevelEnum.HIGH,
        "tier": EscalationTierEnum.TIER_3_MANAGER,
        "auto_resolvable": False,
        "description": "Merchant settlement breached RBI T+1 statutory settlement timeline."
    }
}


class ExceptionClassifier:
    """
    Classifies unmatched records into the 18 specific exception categories with severity and SLA deadlines.
    """

    def classify_exceptions(
        self,
        unmatched_internal: List[CanonicalTransaction],
        unmatched_external: List[CanonicalTransaction],
        parse_errors: List[Dict[str, Any]],
        run_id: str
    ) -> List[ExceptionItem]:
        exceptions: List[ExceptionItem] = []
        now = datetime.now(timezone.utc)

        # 1. Classify Ingestion Format Errors
        for pe in parse_errors:
            meta = CATEGORY_METADATA[ExceptionCategoryEnum.FORMAT_ERROR]
            exc = ExceptionItem(
                exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                run_id=run_id,
                category=ExceptionCategoryEnum.FORMAT_ERROR,
                severity=meta["severity"],
                status=ExceptionStatusEnum.OPEN,
                assigned_tier=meta["tier"],
                bank_code=pe.get("bank_code", "UNKNOWN"),
                affected_amount="0.00",
                currency="INR",
                description=f"Parsing error: {pe.get('error', 'Malformed payload')}",
                suggested_resolution="Inspect raw file schema or update bank configuration YAML.",
                sla_minutes=meta["sla_minutes"],
                created_at=now,
                sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                auto_resolvable=meta["auto_resolvable"]
            )
            exceptions.append(exc)

        # 2. Check for Duplicate Internal Transactions
        seen_internal_refs: Dict[str, CanonicalTransaction] = {}
        dup_internal_ids = set()
        for int_txn in unmatched_internal:
            ref = int_txn.txn_id or int_txn.bank_ref
            if ref in seen_internal_refs:
                dup_internal_ids.add(int_txn.txn_id)
                meta = CATEGORY_METADATA[ExceptionCategoryEnum.DUPLICATE_INTERNAL]
                exc = ExceptionItem(
                    exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    category=ExceptionCategoryEnum.DUPLICATE_INTERNAL,
                    severity=meta["severity"],
                    status=ExceptionStatusEnum.OPEN,
                    assigned_tier=meta["tier"],
                    bank_code=int_txn.bank_code,
                    internal_txn_id=int_txn.txn_id,
                    affected_amount=str(int_txn.amount),
                    currency=int_txn.currency,
                    description=f"Duplicate internal entry detected for reference '{ref}'.",
                    suggested_resolution="Auto-void duplicate record and retain original transaction.",
                    sla_minutes=meta["sla_minutes"],
                    created_at=now,
                    sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                    auto_resolvable=True
                )
                exceptions.append(exc)
            else:
                seen_internal_refs[ref] = int_txn

        # 3. Check for Duplicate External Transactions
        seen_external_refs: Dict[str, CanonicalTransaction] = {}
        dup_external_ids = set()
        for ext_txn in unmatched_external:
            ref = ext_txn.txn_id or ext_txn.bank_ref
            if ref in seen_external_refs:
                dup_external_ids.add(ext_txn.txn_id)
                meta = CATEGORY_METADATA[ExceptionCategoryEnum.DUPLICATE_EXTERNAL]
                exc = ExceptionItem(
                    exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    category=ExceptionCategoryEnum.DUPLICATE_EXTERNAL,
                    severity=meta["severity"],
                    status=ExceptionStatusEnum.OPEN,
                    assigned_tier=meta["tier"],
                    bank_code=ext_txn.bank_code,
                    external_txn_id=ext_txn.txn_id,
                    affected_amount=str(ext_txn.amount),
                    currency=ext_txn.currency,
                    description=f"Bank statement duplicate entry for ref '{ref}'. Possible duplicate batch.",
                    suggested_resolution="Verify bank statement batch hash and check for duplicate file ingestion.",
                    sla_minutes=meta["sla_minutes"],
                    created_at=now,
                    sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                    auto_resolvable=False
                )
                exceptions.append(exc)
            else:
                seen_external_refs[ref] = ext_txn

        # 4. Compare remaining unmatched internal vs external for specific mismatches
        matched_pairs_checked = set()

        for int_txn in unmatched_internal:
            if int_txn.txn_id in dup_internal_ids:
                continue

            found_specific = False
            for ext_txn in unmatched_external:
                if ext_txn.txn_id in dup_external_ids:
                    continue

                pair_key = (int_txn.txn_id, ext_txn.txn_id)
                if pair_key in matched_pairs_checked:
                    continue

                ref_sim = compute_reference_similarity(int_txn.txn_id, ext_txn.txn_id)

                # Check DIRECTION_REVERSAL
                if ref_sim >= 0.90 and abs(int_txn.amount - ext_txn.amount) <= Decimal("0.01") and int_txn.direction != ext_txn.direction:
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.DIRECTION_REVERSAL]
                    # Check if critical value
                    sev = SeverityLevelEnum.CRITICAL if int_txn.amount >= Decimal("1000000") else meta["severity"]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.DIRECTION_REVERSAL,
                        severity=sev,
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=int_txn.currency,
                        description=f"Direction reversed: Internal is {int_txn.direction.value}, External is {ext_txn.direction.value}.",
                        suggested_resolution="Immediate compliance escalation: review booking instruction & reverse entry.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=False
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check AMOUNT_MISMATCH
                if ref_sim >= 0.90 and abs(int_txn.amount - ext_txn.amount) > Decimal("0.01") and int_txn.direction == ext_txn.direction:
                    diff = abs(int_txn.amount - ext_txn.amount)
                    # Check if small fee deduction
                    if Decimal("0.01") < diff <= Decimal("50.00") and "FEE" in (ext_txn.narration or "").upper():
                        cat = ExceptionCategoryEnum.FEE_DEDUCTION
                    else:
                        cat = ExceptionCategoryEnum.AMOUNT_MISMATCH

                    meta = CATEGORY_METADATA[cat]
                    sev = SeverityLevelEnum.CRITICAL if diff >= Decimal("1000000") else meta["severity"]
                    tier = EscalationTierEnum.TIER_3_MANAGER if diff >= Decimal("1000000") else meta["tier"]

                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=cat,
                        severity=sev,
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=tier,
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(diff),
                        currency=int_txn.currency,
                        description=f"Amount difference of {diff} {int_txn.currency} (Internal: {int_txn.amount}, External: {ext_txn.amount}).",
                        suggested_resolution="Verify fee structure or post adjustment entry." if cat == ExceptionCategoryEnum.FEE_DEDUCTION else "Review bank debit note / merchant payment gateway charges.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=meta["auto_resolvable"]
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check REFERENCE_TRUNCATED
                is_truncated_prefix = (
                    (int_txn.txn_id.startswith(ext_txn.txn_id) or ext_txn.txn_id.startswith(int_txn.txn_id))
                    and len(ext_txn.txn_id) <= 16
                    and len(int_txn.txn_id) > len(ext_txn.txn_id)
                    and abs(int_txn.amount - ext_txn.amount) <= Decimal("0.01")
                )
                if is_truncated_prefix:
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.REFERENCE_TRUNCATED]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.REFERENCE_TRUNCATED,
                        severity=meta["severity"],
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=int_txn.currency,
                        description=f"Bank truncated reference number beyond 16 characters (Internal: '{int_txn.txn_id}', Bank: '{ext_txn.txn_id}').",
                        suggested_resolution="Auto-resolve via prefix alphanumeric matching rule.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=True
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check REGULATORY_HOLD
                if ("AML" in (int_txn.narration or "").upper() or 
                    "HOLD" in (ext_txn.narration or "").upper() or
                    "COMPLIANCE" in (int_txn.narration or "").upper()):
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.REGULATORY_HOLD]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.REGULATORY_HOLD,
                        severity=SeverityLevelEnum.CRITICAL,
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=EscalationTierEnum.TIER_4_COMPLIANCE,
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=int_txn.currency,
                        description=f"Transaction flagged for AML/CFT or FIU-IND compliance hold.",
                        suggested_resolution="Notify compliance team and prepare FIU-IND Suspicious Transaction Report (STR).",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=False
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check REVERSAL_PENDING
                if ("REV" in (ext_txn.narration or "").upper() or 
                    "REVERSAL" in (int_txn.narration or "").upper() or
                    "REFUND" in (int_txn.narration or "").upper()):
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.REVERSAL_PENDING]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.REVERSAL_PENDING,
                        severity=meta["severity"],
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=int_txn.currency,
                        description=f"Transaction marked for reversal but bank reversal entry pending settlement.",
                        suggested_resolution="Monitor next settlement window for reversal credit/debit advice.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=False
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check TIMEZONE_OFFSET
                time_diff_sec = abs((int_txn.txn_date - ext_txn.txn_date).total_seconds())
                is_tz_offset = (
                    ref_sim >= 0.90 
                    and abs(int_txn.amount - ext_txn.amount) <= Decimal("0.01")
                    and int_txn.direction == ext_txn.direction
                    and time_diff_sec <= 86400
                    and int_txn.txn_date.date() != ext_txn.txn_date.date()
                    and (int_txn.txn_date.hour >= 20 or int_txn.txn_date.hour <= 4 or ext_txn.txn_date.hour >= 20 or ext_txn.txn_date.hour <= 4)
                )
                if is_tz_offset:
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.TIMEZONE_OFFSET]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.TIMEZONE_OFFSET,
                        severity=meta["severity"],
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=int_txn.currency,
                        description=f"Date difference caused by timezone offset crossing midnight window ({int_txn.txn_date} vs {ext_txn.txn_date}).",
                        suggested_resolution="Auto-resolve via UTC standardisation re-match.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=True
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check DATE_MISMATCH
                if (ref_sim >= 0.90 
                    and abs(int_txn.amount - ext_txn.amount) <= Decimal("0.01")
                    and int_txn.direction == ext_txn.direction
                    and abs((int_txn.txn_date.date() - ext_txn.txn_date.date()).days) >= 1):
                    days_diff = abs((int_txn.txn_date.date() - ext_txn.txn_date.date()).days)
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.DATE_MISMATCH]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.DATE_MISMATCH,
                        severity=meta["severity"],
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=int_txn.currency,
                        description=f"Booking date mismatch of {days_diff} days between internal ({int_txn.txn_date.date()}) and bank ({ext_txn.txn_date.date()}).",
                        suggested_resolution="Auto-resolve if within T+1, otherwise route to analyst queue.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=(days_diff <= 1)
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check PARTIAL_MATCH
                if ref_sim >= 0.90 and ext_txn.amount < int_txn.amount and int_txn.direction == ext_txn.direction:
                    meta = CATEGORY_METADATA[ExceptionCategoryEnum.PARTIAL_MATCH]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=ExceptionCategoryEnum.PARTIAL_MATCH,
                        severity=meta["severity"],
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount - ext_txn.amount),
                        currency=int_txn.currency,
                        description=f"Partial settlement match: bank settled {ext_txn.amount} of {int_txn.amount} {int_txn.currency}.",
                        suggested_resolution="Check for secondary split installment settlement file.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=True
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

                # Check CURRENCY_MISMATCH / FX_VARIANCE
                if ref_sim >= 0.90 and int_txn.currency != ext_txn.currency:
                    cat = ExceptionCategoryEnum.FX_VARIANCE if abs(int_txn.amount - ext_txn.amount) > 0 else ExceptionCategoryEnum.CURRENCY_MISMATCH
                    meta = CATEGORY_METADATA[cat]
                    exc = ExceptionItem(
                        exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        category=cat,
                        severity=meta["severity"],
                        status=ExceptionStatusEnum.OPEN,
                        assigned_tier=meta["tier"],
                        bank_code=ext_txn.bank_code,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        affected_amount=str(int_txn.amount),
                        currency=f"{int_txn.currency}/{ext_txn.currency}",
                        description=f"Currency mismatch or FX variance > 1.5% between {int_txn.currency} and {ext_txn.currency}.",
                        suggested_resolution="Verify RBI benchmark rate and adjust conversion ledger.",
                        sla_minutes=meta["sla_minutes"],
                        created_at=now,
                        sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                        auto_resolvable=False
                    )
                    exceptions.append(exc)
                    matched_pairs_checked.add(pair_key)
                    found_specific = True
                    break

            if not found_specific:
                # Check if STALE (> T+5)
                days_old = (now.date() - int_txn.txn_date.date()).days
                cat = ExceptionCategoryEnum.STALE_TRANSACTION if days_old > 5 else ExceptionCategoryEnum.MISSING_EXTERNAL
                meta = CATEGORY_METADATA[cat]
                sev = SeverityLevelEnum.CRITICAL if int_txn.amount >= Decimal("1000000") else meta["severity"]
                tier = EscalationTierEnum.TIER_3_MANAGER if int_txn.amount >= Decimal("1000000") else meta["tier"]

                exc = ExceptionItem(
                    exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    category=cat,
                    severity=sev,
                    status=ExceptionStatusEnum.OPEN,
                    assigned_tier=tier,
                    bank_code=int_txn.bank_code,
                    internal_txn_id=int_txn.txn_id,
                    affected_amount=str(int_txn.amount),
                    currency=int_txn.currency,
                    description=f"Internal transaction '{int_txn.txn_id}' not found in external bank statements (Age: {days_old} days).",
                    suggested_resolution="Contact acquiring bank support to verify settlement file transmission." if cat == ExceptionCategoryEnum.MISSING_EXTERNAL else "Write-off or initiate formal bank inquiry for stale record.",
                    sla_minutes=meta["sla_minutes"],
                    created_at=now,
                    sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                    auto_resolvable=False
                )
                exceptions.append(exc)

        # 5. Remaining Unmatched External Transactions (MISSING_INTERNAL)
        for ext_txn in unmatched_external:
            if ext_txn.txn_id in dup_external_ids:
                continue

            # Check if this external txn was already paired in a specific exception
            already_covered = any(e.external_txn_id == ext_txn.txn_id for e in exceptions)
            if not already_covered:
                meta = CATEGORY_METADATA[ExceptionCategoryEnum.MISSING_INTERNAL]
                sev = SeverityLevelEnum.CRITICAL if ext_txn.amount >= Decimal("1000000") else meta["severity"]
                tier = EscalationTierEnum.TIER_3_MANAGER if ext_txn.amount >= Decimal("1000000") else meta["tier"]

                exc = ExceptionItem(
                    exception_id=f"EXC-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    category=ExceptionCategoryEnum.MISSING_INTERNAL,
                    severity=sev,
                    status=ExceptionStatusEnum.OPEN,
                    assigned_tier=tier,
                    bank_code=ext_txn.bank_code,
                    external_txn_id=ext_txn.txn_id,
                    affected_amount=str(ext_txn.amount),
                    currency=ext_txn.currency,
                    description=f"External bank credit/debit of {ext_txn.amount} {ext_txn.currency} (Ref: {ext_txn.txn_id}) missing in internal ledger.",
                    suggested_resolution="Check gateway webhook delivery or create manual adjustment booking.",
                    sla_minutes=meta["sla_minutes"],
                    created_at=now,
                    sla_deadline=now + timedelta(minutes=meta["sla_minutes"]),
                    auto_resolvable=False
                )
                exceptions.append(exc)

        return exceptions
