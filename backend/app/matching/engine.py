"""
Matching Orchestrator and Three-Tier Execution Engine.
Coordinates sequential execution: Exact Matching -> Fuzzy Matching -> Rule-Based Matching.
"""

import time
from typing import List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime

from backend.app.models.canonical import CanonicalTransaction
from backend.app.models.schemas import MatchResultItem, MatchTypeEnum
from backend.app.matching.exact import run_exact_matching
from backend.app.matching.fuzzy import run_fuzzy_matching
from backend.app.matching.rules import run_rule_based_matching


class MatchingOrchestrator:
    """
    Coordinates multi-tier matching algorithms and aggregates performance metrics.
    """

    def __init__(
        self,
        tolerance_amount: Decimal = Decimal("0.01"),
        tolerance_fx: Decimal = Decimal("0.015"),
        fast_mode: bool = False
    ):
        self.tolerance_amount = tolerance_amount
        self.tolerance_fx = tolerance_fx
        self.fast_mode = fast_mode

    def execute(
        self,
        internal_records: List[CanonicalTransaction],
        external_records: List[CanonicalTransaction],
        run_id: str
    ) -> Tuple[List[MatchResultItem], List[CanonicalTransaction], List[CanonicalTransaction], Dict[str, Any]]:
        """
        Executes the three-stage matching pipeline.
        Returns (all_matches, remaining_unmatched_internal, remaining_unmatched_external, metrics).
        """
        start_time = time.perf_counter()
        metrics = {
            "total_internal": len(internal_records),
            "total_external": len(external_records),
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "rule_matches": 0,
            "split_matches": 0,
            "netted_matches": 0,
            "total_matches": 0,
            "match_rate": 0.0,
            "duration_ms": 0.0,
            "stages": {}
        }

        all_matches: List[MatchResultItem] = []

        # STAGE 1: Exact Hash Matching
        t1_start = time.perf_counter()
        exact_matches, rem_int, rem_ext = run_exact_matching(
            internal_records=internal_records,
            external_records=external_records,
            run_id=run_id
        )
        t1_duration = (time.perf_counter() - t1_start) * 1000
        all_matches.extend(exact_matches)
        metrics["exact_matches"] = len(exact_matches)
        metrics["stages"]["exact"] = {
            "count": len(exact_matches),
            "duration_ms": round(t1_duration, 2),
            "remaining_internal": len(rem_int),
            "remaining_external": len(rem_ext)
        }

        if not self.fast_mode:
            # STAGE 2: Candidate-Blocked Fuzzy Matching
            t2_start = time.perf_counter()
            fuzzy_matches, rem_int, rem_ext = run_fuzzy_matching(
                internal_records=rem_int,
                external_records=rem_ext,
                run_id=run_id,
                tolerance_amount=self.tolerance_amount,
                tolerance_fx=self.tolerance_fx
            )
            t2_duration = (time.perf_counter() - t2_start) * 1000
            all_matches.extend(fuzzy_matches)
            metrics["fuzzy_matches"] = len(fuzzy_matches)
            metrics["stages"]["fuzzy"] = {
                "count": len(fuzzy_matches),
                "duration_ms": round(t2_duration, 2),
                "remaining_internal": len(rem_int),
                "remaining_external": len(rem_ext)
            }

            # STAGE 3: Rule-Based Matching (Split + Netted + Tolerance + Date Calendar)
            t3_start = time.perf_counter()
            rule_matches, rem_int, rem_ext = run_rule_based_matching(
                internal_records=rem_int,
                external_records=rem_ext,
                run_id=run_id,
                tolerance_amount=self.tolerance_amount,
                tolerance_fx=self.tolerance_fx
            )
            t3_duration = (time.perf_counter() - t3_start) * 1000
            all_matches.extend(rule_matches)

            for rm in rule_matches:
                if rm.match_type == MatchTypeEnum.SPLIT:
                    metrics["split_matches"] += 1
                elif rm.match_type == MatchTypeEnum.NETTED:
                    metrics["netted_matches"] += 1
                else:
                    metrics["rule_matches"] += 1

            metrics["stages"]["rule_based"] = {
                "count": len(rule_matches),
                "duration_ms": round(t3_duration, 2),
                "remaining_internal": len(rem_int),
                "remaining_external": len(rem_ext)
            }

        total_duration = (time.perf_counter() - start_time) * 1000
        metrics["total_matches"] = len(all_matches)
        metrics["duration_ms"] = round(total_duration, 2)

        base_total = max(len(internal_records), len(external_records))
        metrics["match_rate"] = round((len(all_matches) / base_total * 100.0) if base_total > 0 else 0.0, 2)

        return all_matches, rem_int, rem_ext, metrics
