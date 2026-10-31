"""
Audit Trail Verifier and Cryptographic Tamper Detection Engine.
Walks the entire block chain, validates hash links, and identifies exact tamper points.
"""

from typing import List, Dict, Any, Tuple
from backend.app.models.schemas import AuditLogItem
from backend.app.audit.logger import compute_entry_hash, GENESIS_HASH


def verify_audit_chain(entries: List[AuditLogItem]) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validates integrity of audit trail:
    1. Recomputes sha256_hash for every entry.
    2. Validates prev_hash links to the immediately preceding block.
    Returns (is_valid, violation_reports).
    """
    if not entries:
        return True, []

    violations: List[Dict[str, Any]] = []
    expected_prev_hash = GENESIS_HASH

    for index, entry in enumerate(entries):
        # Check prev_hash link
        if entry.prev_hash != expected_prev_hash:
            violations.append({
                "index": index,
                "event_id": entry.event_id,
                "error_type": "PREV_HASH_MISMATCH",
                "expected_prev_hash": expected_prev_hash,
                "actual_prev_hash": entry.prev_hash,
                "details": f"Broken chain link at block index {index}."
            })

        # Recompute hash
        recomputed = compute_entry_hash(
            event_id=entry.event_id,
            timestamp_str=entry.timestamp.isoformat(),
            actor=entry.actor,
            action_type=entry.action_type,
            affected_records=entry.affected_records,
            before_state=entry.before_state,
            after_state=entry.after_state,
            rationale=entry.rationale,
            prev_hash=entry.prev_hash
        )

        if recomputed != entry.sha256_hash:
            violations.append({
                "index": index,
                "event_id": entry.event_id,
                "error_type": "HASH_CORRUPTION",
                "recorded_hash": entry.sha256_hash,
                "recalculated_hash": recomputed,
                "details": f"Data integrity violation in block {entry.event_id}."
            })
            entry.is_valid = False
        else:
            entry.is_valid = True

        expected_prev_hash = entry.sha256_hash

    is_valid = len(violations) == 0
    return is_valid, violations
