"""
Unit and Integration tests for Matching Algorithms (Exact, Fuzzy, Rules, Split & Netted).
"""

from decimal import Decimal
from datetime import datetime

from backend.app.models.canonical import CanonicalTransaction, DirectionEnum, SourceFormatEnum
from backend.app.matching.exact import run_exact_matching
from backend.app.matching.fuzzy import run_fuzzy_matching
from backend.app.matching.rules import run_rule_based_matching, find_subset_sum
from backend.app.matching.engine import MatchingOrchestrator


def make_txn(txn_id: str, amount: str, direction: DirectionEnum = DirectionEnum.CR, cp: str = "MERCHANT"):
    return CanonicalTransaction(
        txn_id=txn_id,
        txn_date=datetime(2026, 3, 15, 12, 0, 0),
        amount=Decimal(amount),
        currency="INR",
        direction=direction,
        counterparty_name=cp,
        bank_ref=txn_id
    )


def test_exact_matching():
    internal = [make_txn("PB001", "1500.00"), make_txn("PB002", "2500.00")]
    external = [make_txn("PB001", "1500.00"), make_txn("PB003", "3500.00")]

    matches, rem_int, rem_ext = run_exact_matching(internal, external, "RUN-TEST")
    assert len(matches) == 1
    assert matches[0].internal_txn_id == "PB001"
    assert len(rem_int) == 1
    assert len(rem_ext) == 1


def test_fuzzy_matching_jaro_winkler():
    # Minor character difference in reference (edit distance 1)
    internal = [make_txn("PB26031500000099", "1500.00", cp="AMAZON PAY INDIA")]
    external = [make_txn("PB26031500000098", "1500.00", cp="AMAZON PAY")]

    matches, rem_int, rem_ext = run_fuzzy_matching(internal, external, "RUN-TEST")
    assert len(matches) == 1
    assert matches[0].confidence_score >= 0.85


def test_split_transaction_subset_sum():
    # 1 external record of 3000.00 matches 2 internal records of 1000.00 and 2000.00
    internal = [make_txn("PB-SPLIT-1", "1000.00"), make_txn("PB-SPLIT-2", "2000.00")]
    external = [make_txn("EXT-3000", "3000.00")]

    subset = find_subset_sum(internal, Decimal("3000.00"), tolerance=Decimal("0.01"))
    assert subset is not None
    assert len(subset) == 2

    matches, rem_int, rem_ext = run_rule_based_matching(internal, external, "RUN-TEST")
    assert len(matches) == 1
    assert matches[0].match_type.value == "SPLIT"
    assert len(matches[0].internal_txn_ids) == 2
