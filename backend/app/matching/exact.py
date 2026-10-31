"""
O(N+M) Exact Matching Engine using Hash Indices and Collision Disambiguation.
"""

from typing import List, Dict, Tuple, Set
from decimal import Decimal
import uuid
from datetime import datetime, timezone

from backend.app.models.canonical import CanonicalTransaction
from backend.app.models.schemas import MatchResultItem, MatchTypeEnum


def build_composite_key(txn: CanonicalTransaction, use_bank_ref: bool = False) -> str:
    """Builds composite hash key: id|amount|currency|direction."""
    ref = txn.bank_ref if (use_bank_ref and txn.bank_ref) else txn.txn_id
    clean_ref = str(ref).strip().upper()
    return f"{clean_ref}|{txn.amount}|{txn.currency}|{txn.direction.value}"


def run_exact_matching(
    internal_records: List[CanonicalTransaction],
    external_records: List[CanonicalTransaction],
    run_id: str
) -> Tuple[List[MatchResultItem], List[CanonicalTransaction], List[CanonicalTransaction]]:
    """
    Performs exact hash matching between internal and external records.
    Returns (matched_items, remaining_internal, remaining_external).
    """
    matches: List[MatchResultItem] = []
    
    # Hash table for external records: key -> list of external txns (to handle collisions)
    external_map: Dict[str, List[CanonicalTransaction]] = {}
    
    for ext in external_records:
        key1 = build_composite_key(ext, use_bank_ref=False)
        external_map.setdefault(key1, []).append(ext)
        if ext.bank_ref and ext.bank_ref != ext.txn_id:
            key2 = build_composite_key(ext, use_bank_ref=True)
            if key2 != key1:
                external_map.setdefault(key2, []).append(ext)

    matched_internal_ids: Set[str] = set()
    matched_external_ids: Set[str] = set()

    for int_txn in internal_records:
        if int_txn.txn_id in matched_internal_ids:
            continue

        # Try key by txn_id
        candidate_keys = [
            build_composite_key(int_txn, use_bank_ref=False)
        ]
        if int_txn.bank_ref:
            candidate_keys.append(build_composite_key(int_txn, use_bank_ref=True))

        target_ext_list = None
        for k in candidate_keys:
            if k in external_map and external_map[k]:
                target_ext_list = external_map[k]
                break

        if target_ext_list:
            # Find candidate not yet matched
            chosen_ext = None
            for ext in target_ext_list:
                if ext.txn_id not in matched_external_ids:
                    chosen_ext = ext
                    break

            if chosen_ext:
                matched_internal_ids.add(int_txn.txn_id)
                matched_external_ids.add(chosen_ext.txn_id)

                match_item = MatchResultItem(
                    match_id=f"EXACT-{uuid.uuid4().hex[:12].upper()}",
                    run_id=run_id,
                    internal_txn_id=int_txn.txn_id,
                    external_txn_id=chosen_ext.txn_id,
                    internal_txn_ids=[int_txn.txn_id],
                    external_txn_ids=[chosen_ext.txn_id],
                    match_type=MatchTypeEnum.EXACT,
                    confidence_score=1.00,
                    rule_name="EXACT_HASH_COMPOSITE_MATCH",
                    internal_amount=str(int_txn.amount),
                    external_amount=str(chosen_ext.amount),
                    amount_diff="0.0000",
                    bank_code=chosen_ext.bank_code or int_txn.bank_code,
                    matched_at=datetime.now(timezone.utc),
                    breakdown={
                        "reference": 1.0,
                        "amount": 1.0,
                        "date": 1.0,
                        "counterparty": 1.0,
                        "direction": 1.0,
                        "currency": 1.0,
                        "composite": 1.0
                    }
                )
                matches.append(match_item)

    remaining_internal = [t for t in internal_records if t.txn_id not in matched_internal_ids]
    remaining_external = [t for t in external_records if t.txn_id not in matched_external_ids]

    return matches, remaining_internal, remaining_external
