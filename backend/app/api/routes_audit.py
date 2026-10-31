"""
Cryptographic Audit Trail and Tamper Verification API Routes.
"""

from typing import Optional, List
from fastapi import APIRouter, Query

from backend.app.audit.logger import global_audit_logger
from backend.app.audit.verifier import verify_audit_chain
from backend.app.models.schemas import AuditLogItem

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


@router.get("")
def get_audit_trail(
    action_type: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Returns immutable audit log events with SHA-256 hash chains.
    """
    all_entries = global_audit_logger.get_entries(action_type=action_type, actor=actor, limit=1000)
    # Reverse to show newest first
    reversed_entries = list(reversed(all_entries))

    # Verify chain
    is_valid, violations = verify_audit_chain(all_entries)

    return {
        "total_entries": len(all_entries),
        "is_chain_valid": is_valid,
        "genesis_anchor": "0" * 64,
        "latest_hash": global_audit_logger.last_hash,
        "limit": limit,
        "offset": offset,
        "entries": reversed_entries[offset:offset+limit]
    }


@router.get("/verify")
def run_audit_verification():
    """
    Executes full cryptographic verification on all blocks in the audit trail.
    Recalculates SHA-256 for each entry and validates prev_hash consistency.
    """
    entries = global_audit_logger._entries
    is_valid, violations = verify_audit_chain(entries)

    return {
        "status": "VALID" if is_valid else "CORRUPTED",
        "is_valid": is_valid,
        "total_blocks_checked": len(entries),
        "violations_found": len(violations),
        "violations": violations,
        "verification_method": "SHA-256 Merkle-like Hash Chain",
        "retention_standard": "Companies Act 2013 (Sec 128) 10-Year Storage"
    }
