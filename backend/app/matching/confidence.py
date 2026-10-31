"""
Confidence scoring and similarity metrics engine.
Calculates 6-factor weighted similarity score per Section A3.4 specification.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Tuple, Dict
from rapidfuzz import distance, fuzz

from backend.app.models.canonical import CanonicalTransaction, DirectionEnum

# Weights defined in Section A3.4
WEIGHTS = {
    "reference": 0.35,
    "amount": 0.25,
    "date": 0.15,
    "counterparty": 0.10,
    "direction": 0.10,
    "currency": 0.05
}

AUTO_MATCH_THRESHOLD = 0.85
HUMAN_REVIEW_THRESHOLD = 0.60


def compute_reference_similarity(ref1: str, ref2: str) -> float:
    """Calculates reference similarity using Exact, Jaro-Winkler, and Levenshtein."""
    if not ref1 or not ref2:
        return 0.0
    r1 = ref1.strip().upper()
    r2 = ref2.strip().upper()

    if r1 == r2:
        return 1.0

    # Jaro-Winkler similarity (threshold 0.92)
    jw_score = distance.JaroWinkler.similarity(r1, r2)
    if jw_score >= 0.92:
        return float(jw_score)

    # Levenshtein distance check for strings > 12 chars
    if len(r1) >= 12 and len(r2) >= 12:
        lev_dist = distance.Levenshtein.distance(r1, r2)
        if lev_dist <= 2:
            return 0.88 - (lev_dist * 0.04)

    # Prefix match check (e.g. truncated reference)
    if (len(r1) >= 10 and len(r2) >= 10) and (r1.startswith(r2[:10]) or r2.startswith(r1[:10])):
        return 0.80

    return 0.0


def compute_amount_similarity(
    amt1: Decimal,
    amt2: Decimal,
    tolerance: Decimal = Decimal("0.01"),
    fx_mode: bool = False,
    tolerance_fx: Decimal = Decimal("0.015")
) -> float:
    """Calculates amount similarity with same-currency and cross-currency FX tolerance."""
    if amt1 == amt2:
        return 1.0

    diff = abs(amt1 - amt2)
    if not fx_mode:
        if diff <= tolerance:
            return 0.95
    else:
        # Cross currency % variance
        mean_amt = (abs(amt1) + abs(amt2)) / Decimal("2.0")
        if mean_amt > 0:
            variance_pct = diff / mean_amt
            if variance_pct <= tolerance_fx:
                return 0.85

    return 0.0


def compute_date_similarity(d1: date | datetime, d2: date | datetime) -> float:
    """Calculates temporal proximity score (Same date = 1.0, T+1 = 0.8, T+2 = 0.5, T+3 = 0.2)."""
    date1 = d1.date() if isinstance(d1, datetime) else d1
    date2 = d2.date() if isinstance(d2, datetime) else d2

    diff_days = abs((date1 - date2).days)
    if diff_days == 0:
        return 1.0
    elif diff_days == 1:
        return 0.8
    elif diff_days == 2:
        return 0.5
    elif diff_days == 3:
        return 0.2
    return 0.0


def compute_counterparty_similarity(name1: str, name2: str) -> float:
    """Calculates counterparty similarity using Token Set Ratio (threshold 0.80)."""
    if not name1 or not name2:
        return 0.5  # Neutral default if counterparty missing

    n1 = name1.strip().upper()
    n2 = name2.strip().upper()
    if n1 == n2:
        return 1.0

    ratio = fuzz.token_set_ratio(n1, n2) / 100.0
    if ratio >= 0.80:
        return float(ratio)
    elif ratio >= 0.65:
        return float(ratio * 0.7)
    return 0.0


def compute_confidence_score(
    internal_txn: CanonicalTransaction,
    external_txn: CanonicalTransaction,
    tolerance_amount: Decimal = Decimal("0.01"),
    tolerance_fx: Decimal = Decimal("0.015")
) -> Tuple[float, Dict[str, float]]:
    """
    Computes overall confidence score between internal and external records.
    Returns (composite_score, field_breakdown).
    """
    # 1. Direction: Must match (or credit to debit correspondence)
    # External Credit means money received by aggregator (Internal Credit/Debit depending on perspective)
    # If directions are exact match:
    dir_score = 1.0 if internal_txn.direction == external_txn.direction else 0.0
    if dir_score == 0.0:
        # If direction is reversed, return 0 for auto-matching and route to exception
        return 0.0, {"direction": 0.0}

    # 2. Currency
    is_fx = internal_txn.currency != external_txn.currency
    curr_score = 1.0 if not is_fx else 0.8

    # 3. Reference (Compare both txn_id and bank_ref)
    ref_candidates = [
        compute_reference_similarity(internal_txn.txn_id, external_txn.txn_id),
        compute_reference_similarity(internal_txn.txn_id, external_txn.bank_ref),
        compute_reference_similarity(internal_txn.bank_ref, external_txn.bank_ref),
        compute_reference_similarity(internal_txn.bank_ref, external_txn.txn_id)
    ]
    ref_score = max(ref_candidates)

    # 4. Amount
    amt_score = compute_amount_similarity(
        internal_txn.amount,
        external_txn.amount,
        tolerance=tolerance_amount,
        fx_mode=is_fx,
        tolerance_fx=tolerance_fx
    )

    # 5. Date
    date_score = compute_date_similarity(internal_txn.txn_date, external_txn.txn_date)

    # 6. Counterparty
    cp_score = compute_counterparty_similarity(internal_txn.counterparty_name, external_txn.counterparty_name)

    # Weighted sum
    composite = (
        (ref_score * WEIGHTS["reference"]) +
        (amt_score * WEIGHTS["amount"]) +
        (date_score * WEIGHTS["date"]) +
        (cp_score * WEIGHTS["counterparty"]) +
        (dir_score * WEIGHTS["direction"]) +
        (curr_score * WEIGHTS["currency"])
    )

    breakdown = {
        "reference": round(ref_score, 4),
        "amount": round(amt_score, 4),
        "date": round(date_score, 4),
        "counterparty": round(cp_score, 4),
        "direction": round(dir_score, 4),
        "currency": round(curr_score, 4),
        "composite": round(composite, 4)
    }

    return round(composite, 4), breakdown
