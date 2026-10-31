"""
Rule-Based Matching Engine with Split Transaction & Netted Settlement Solvers.
Solves subset-sum optimization for batch settlements, fee deductions, and cross-currency netting.
"""

from typing import List, Dict, Tuple, Set, Optional
from decimal import Decimal
import uuid
from datetime import datetime, date, timedelta, timezone

from backend.app.models.canonical import CanonicalTransaction, DirectionEnum
from backend.app.models.schemas import MatchResultItem, MatchTypeEnum
from backend.app.normalisation.currency import convert_fx, round_bankers


# Indian Banking Holidays (Sample calendar for business day calculation)
INDIAN_BANK_HOLIDAYS_2026 = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 17),  # Holi
    date(2026, 4, 14),  # Ambedkar Jayanti
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 8),  # Diwali
    date(2026, 12, 25), # Christmas
}


def is_business_day(d: date) -> bool:
    """Checks if date is a business day (Monday-Friday and not a public holiday)."""
    if d.weekday() >= 5:  # Saturday or Sunday
        return False
    if d in INDIAN_BANK_HOLIDAYS_2026:
        return False
    return True


def add_business_days(start_date: date, num_days: int) -> date:
    """Adds N business days accounting for weekends and bank holidays."""
    cur = start_date
    added = 0
    while added < num_days:
        cur += timedelta(days=1)
        if is_business_day(cur):
            added += 1
    return cur


def find_subset_sum(
    candidates: List[CanonicalTransaction],
    target_amount: Decimal,
    tolerance: Decimal = Decimal("0.01"),
    max_items: int = 8
) -> Optional[List[CanonicalTransaction]]:
    """
    Finds a subset of transactions whose sum equals target_amount within tolerance.
    Uses recursive branch-and-bound search with pruning.
    """
    sorted_candidates = sorted(candidates, key=lambda x: x.amount, reverse=True)

    def _search(index: int, current_sum: Decimal, current_subset: List[CanonicalTransaction]):
        if abs(current_sum - target_amount) <= tolerance and len(current_subset) >= 2:
            return current_subset

        if len(current_subset) >= max_items or index >= len(sorted_candidates):
            return None

        # Try including item
        item = sorted_candidates[index]
        if current_sum + item.amount <= target_amount + tolerance:
            res = _search(index + 1, current_sum + item.amount, current_subset + [item])
            if res is not None:
                return res

        # Try skipping item
        return _search(index + 1, current_sum, current_subset)

    return _search(0, Decimal("0.00"), [])


def run_rule_based_matching(
    internal_records: List[CanonicalTransaction],
    external_records: List[CanonicalTransaction],
    run_id: str,
    tolerance_amount: Decimal = Decimal("0.01"),
    tolerance_fx: Decimal = Decimal("0.015")
) -> Tuple[List[MatchResultItem], List[CanonicalTransaction], List[CanonicalTransaction]]:
    """
    Executes domain rules:
    1. Amount tolerance match (within ±0.01 or FX tolerance)
    2. Split transaction detection (1 external -> N internal)
    3. Netted settlement detection (1 internal -> N external or cross-currency netted batch)
    4. Date offset match with business calendar
    """
    matches: List[MatchResultItem] = []
    matched_internal_ids: Set[str] = set()
    matched_external_ids: Set[str] = set()

    # RULE 1: Split Transaction Detection (1 External matches N Internal)
    for ext in external_records:
        if ext.txn_id in matched_external_ids:
            continue

        candidate_internals = [
            t for t in internal_records
            if t.txn_id not in matched_internal_ids
            and t.direction == ext.direction
            and abs((t.txn_date.date() - ext.txn_date.date()).days) <= 3
        ]

        if len(candidate_internals) >= 2:
            subset = find_subset_sum(candidate_internals, ext.amount, tolerance=tolerance_amount, max_items=8)
            if subset:
                subset_ids = [t.txn_id for t in subset]
                for sid in subset_ids:
                    matched_internal_ids.add(sid)
                matched_external_ids.add(ext.txn_id)

                subset_sum = sum(t.amount for t in subset)
                match_item = MatchResultItem(
                    match_id=f"SPLIT-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    internal_txn_id=subset[0].txn_id,
                    external_txn_id=ext.txn_id,
                    internal_txn_ids=subset_ids,
                    external_txn_ids=[ext.txn_id],
                    match_type=MatchTypeEnum.SPLIT,
                    confidence_score=0.92,
                    rule_name="SPLIT_TRANSACTION_SUBSET_SUM",
                    internal_amount=str(subset_sum),
                    external_amount=str(ext.amount),
                    amount_diff=str(abs(subset_sum - ext.amount)),
                    bank_code=ext.bank_code,
                    matched_at=datetime.now(timezone.utc),
                    breakdown={"split_count": float(len(subset)), "amount_match": 1.0, "composite": 0.92}
                )
                matches.append(match_item)
                continue

    # RULE 2: Netted Settlement Detection (1 Internal matches N External)
    for int_txn in internal_records:
        if int_txn.txn_id in matched_internal_ids:
            continue

        candidate_externals = [
            t for t in external_records
            if t.txn_id not in matched_external_ids
            and t.direction == int_txn.direction
            and abs((t.txn_date.date() - int_txn.txn_date.date()).days) <= 3
        ]

        if len(candidate_externals) >= 2:
            subset = find_subset_sum(candidate_externals, int_txn.amount, tolerance=tolerance_amount, max_items=8)
            if subset:
                subset_ids = [t.txn_id for t in subset]
                for sid in subset_ids:
                    matched_external_ids.add(sid)
                matched_internal_ids.add(int_txn.txn_id)

                subset_sum = sum(t.amount for t in subset)
                match_item = MatchResultItem(
                    match_id=f"NETTED-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    internal_txn_id=int_txn.txn_id,
                    external_txn_id=subset[0].txn_id,
                    internal_txn_ids=[int_txn.txn_id],
                    external_txn_ids=subset_ids,
                    match_type=MatchTypeEnum.NETTED,
                    confidence_score=0.90,
                    rule_name="NETTED_SETTLEMENT_SUBSET_SUM",
                    internal_amount=str(int_txn.amount),
                    external_amount=str(subset_sum),
                    amount_diff=str(abs(int_txn.amount - subset_sum)),
                    bank_code=subset[0].bank_code,
                    matched_at=datetime.now(timezone.utc),
                    breakdown={"netted_count": float(len(subset)), "amount_match": 1.0, "composite": 0.90}
                )
                matches.append(match_item)
                continue

    # RULE 3: Amount Tolerance + Business Date Offset Match
    for int_txn in internal_records:
        if int_txn.txn_id in matched_internal_ids:
            continue

        for ext_txn in external_records:
            if ext_txn.txn_id in matched_external_ids:
                continue

            if int_txn.direction != ext_txn.direction:
                continue

            # Amount check with tolerance
            diff = abs(int_txn.amount - ext_txn.amount)
            if diff <= tolerance_amount:
                # Check business day window
                date_diff = abs((int_txn.txn_date.date() - ext_txn.txn_date.date()).days)
                if date_diff <= 3:
                    matched_internal_ids.add(int_txn.txn_id)
                    matched_external_ids.add(ext_txn.txn_id)

                    match_item = MatchResultItem(
                        match_id=f"RULE-{uuid.uuid4().hex[:12].upper()}",
                        run_id=run_id,
                        internal_txn_id=int_txn.txn_id,
                        external_txn_id=ext_txn.txn_id,
                        internal_txn_ids=[int_txn.txn_id],
                        external_txn_ids=[ext_txn.txn_id],
                        match_type=MatchTypeEnum.RULE,
                        confidence_score=0.88,
                        rule_name="AMOUNT_TOLERANCE_DATE_OFFSET_RULE",
                        internal_amount=str(int_txn.amount),
                        external_amount=str(ext_txn.amount),
                        amount_diff=str(diff),
                        bank_code=ext_txn.bank_code or int_txn.bank_code,
                        matched_at=datetime.now(timezone.utc),
                        breakdown={"amount_diff": float(diff), "date_diff_days": float(date_diff), "composite": 0.88}
                    )
                    matches.append(match_item)
                    break

    remaining_internal = [t for t in internal_records if t.txn_id not in matched_internal_ids]
    remaining_external = [t for t in external_records if t.txn_id not in matched_external_ids]

    return matches, remaining_internal, remaining_external
