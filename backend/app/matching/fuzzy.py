"""
Candidate-Blocked Fuzzy Matching Engine using RapidFuzz.
Applies Jaro-Winkler, Levenshtein, and Token Set Ratio across blocked candidate pools.
"""

from typing import List, Dict, Tuple, Set
from decimal import Decimal
import uuid
from datetime import datetime, date, timedelta, timezone

from backend.app.models.canonical import CanonicalTransaction
from backend.app.models.schemas import MatchResultItem, MatchTypeEnum
from backend.app.matching.confidence import compute_confidence_score, AUTO_MATCH_THRESHOLD, HUMAN_REVIEW_THRESHOLD


def run_fuzzy_matching(
    internal_records: List[CanonicalTransaction],
    external_records: List[CanonicalTransaction],
    run_id: str,
    tolerance_amount: Decimal = Decimal("0.01"),
    tolerance_fx: Decimal = Decimal("0.015")
) -> Tuple[List[MatchResultItem], List[CanonicalTransaction], List[CanonicalTransaction]]:
    """
    Performs fuzzy matching on remaining unmatched records.
    Uses candidate blocking (amount ± tolerance, date ± 2 days) to guarantee O(N) candidate evaluation.
    """
    matches: List[MatchResultItem] = []
    matched_internal_ids: Set[str] = set()
    matched_external_ids: Set[str] = set()

    # Candidate blocking index: (date, direction) -> list of external txns
    from collections import defaultdict
    ext_block_index: Dict[Tuple[date, DirectionEnum], List[CanonicalTransaction]] = defaultdict(list)
    for ext in external_records:
        ext_block_index[(ext.txn_date.date(), ext.direction)].append(ext)

    for int_txn in internal_records:
        if int_txn.txn_id in matched_internal_ids:
            continue

        best_score = 0.0
        best_candidate = None
        best_breakdown = {}

        # Candidate blocking: only check records within ±2 days and identical direction
        int_d = int_txn.txn_date.date()
        candidate_pool: List[CanonicalTransaction] = []
        for offset in (-2, -1, 0, 1, 2):
            target_d = int_d + timedelta(days=offset)
            candidate_pool.extend(ext_block_index.get((target_d, int_txn.direction), []))

        for ext_txn in candidate_pool:
            if ext_txn.txn_id in matched_external_ids:
                continue

            # Amount proximity fast prune: if diff > 50 and not FX, skip
            if int_txn.currency == ext_txn.currency and abs(int_txn.amount - ext_txn.amount) > Decimal("50.00"):
                continue

            score, breakdown = compute_confidence_score(
                int_txn,
                ext_txn,
                tolerance_amount=tolerance_amount,
                tolerance_fx=tolerance_fx
            )

            if score > best_score:
                best_score = score
                best_candidate = ext_txn
                best_breakdown = breakdown
                if score >= 0.98:
                    break  # Early exit on near-exact score

        if best_candidate and best_score >= HUMAN_REVIEW_THRESHOLD:
            matched_internal_ids.add(int_txn.txn_id)
            matched_external_ids.add(best_candidate.txn_id)

            match_item = MatchResultItem(
                match_id=f"FUZZY-{uuid.uuid4().hex[:12].upper()}",
                run_id=run_id,
                internal_txn_id=int_txn.txn_id,
                external_txn_id=best_candidate.txn_id,
                internal_txn_ids=[int_txn.txn_id],
                external_txn_ids=[best_candidate.txn_id],
                match_type=MatchTypeEnum.FUZZY,
                confidence_score=best_score,
                rule_name="RAPIDFUZZ_WEIGHTED_CONFIDENCE",
                internal_amount=str(int_txn.amount),
                external_amount=str(best_candidate.amount),
                amount_diff=str(abs(int_txn.amount - best_candidate.amount)),
                bank_code=best_candidate.bank_code or int_txn.bank_code,
                matched_at=datetime.now(timezone.utc),
                breakdown=best_breakdown
            )
            matches.append(match_item)

    remaining_internal = [t for t in internal_records if t.txn_id not in matched_internal_ids]
    remaining_external = [t for t in external_records if t.txn_id not in matched_external_ids]

    return matches, remaining_internal, remaining_external
