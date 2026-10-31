"""
Exception Management, Triage, and Resolution API Routes.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from decimal import Decimal

from backend.app.models.schemas import (
    ExceptionItem, ResolveExceptionRequest, ExceptionStatusEnum,
    ExceptionCategoryEnum, SeverityLevelEnum
)
from backend.app.models.db_service import persist_exceptions
from backend.app.api.routes_recon import RUN_EXCEPTIONS
from backend.app.audit.logger import global_audit_logger

router = APIRouter(prefix="/api/v1/exceptions", tags=["Exceptions"])


@router.get("")
def list_exceptions(
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    bank_code: Optional[str] = None,
    limit: int = 150,
    offset: int = 0
):
    """
    Returns filtered and paginated list of exceptions across all or specific runs.
    """
    all_exceptions: List[ExceptionItem] = []
    if run_id:
        all_exceptions = RUN_EXCEPTIONS.get(run_id, [])
    else:
        for ex_list in RUN_EXCEPTIONS.values():
            all_exceptions.extend(ex_list)

    # Apply filters
    filtered = all_exceptions
    if status:
        filtered = [e for e in filtered if e.status.value.upper() == status.upper()]
    if category:
        filtered = [e for e in filtered if e.category.value.upper() == category.upper()]
    if severity:
        filtered = [e for e in filtered if e.severity.value.upper() == severity.upper()]
    if bank_code:
        filtered = [e for e in filtered if e.bank_code.upper() == bank_code.upper()]

    # Sort critical first, then SLA breach
    sorted_ex = sorted(
        filtered,
        key=lambda x: (
            0 if x.severity == SeverityLevelEnum.CRITICAL else (1 if x.severity == SeverityLevelEnum.HIGH else 2),
            0 if x.is_sla_breached else 1,
            x.sla_deadline
        )
    )

    return {
        "total": len(sorted_ex),
        "open_count": len([e for e in sorted_ex if e.status in (ExceptionStatusEnum.OPEN, ExceptionStatusEnum.ESCALATED)]),
        "sla_breached_count": len([e for e in sorted_ex if e.is_sla_breached]),
        "limit": limit,
        "offset": offset,
        "exceptions": sorted_ex[offset:offset+limit]
    }


@router.get("/{exception_id}")
def get_exception_by_id(exception_id: str):
    """Fetch single exception details."""
    for ex_list in RUN_EXCEPTIONS.values():
        for exc in ex_list:
            if exc.exception_id == exception_id:
                return exc
    raise HTTPException(status_code=404, detail="Exception not found")


@router.put("/{exception_id}/resolve")
def resolve_exception(exception_id: str, req: ResolveExceptionRequest):
    """
    Resolves an exception with human analyst justification and writes an immutable audit record.
    """
    target_exc: Optional[ExceptionItem] = None
    target_run_id = None

    for r_id, ex_list in RUN_EXCEPTIONS.items():
        for exc in ex_list:
            if exc.exception_id == exception_id:
                target_exc = exc
                target_run_id = r_id
                break
        if target_exc:
            break

    if not target_exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    before_state = target_exc.model_dump()

    target_exc.status = ExceptionStatusEnum.RESOLVED
    target_exc.resolution_action = req.resolution_action
    target_exc.resolution_notes = req.resolution_notes
    target_exc.resolved_by = req.resolved_by
    target_exc.resolved_at = datetime.now(timezone.utc)

    after_state = target_exc.model_dump()

    # Persist updated exception to DB
    try:
        persist_exceptions([target_exc])
    except Exception as e:
        print(f"[DB Warning] Could not persist exception to DB: {e}")

    # Log to cryptographic audit log
    global_audit_logger.log_event(
        actor=req.resolved_by,
        action_type="RESOLVE_EXCEPTION",
        affected_records=[exception_id],
        rationale=f"Resolved with action {req.resolution_action}: {req.resolution_notes}",
        before_state=before_state,
        after_state=after_state
    )

    return {
        "status": "SUCCESS",
        "message": f"Exception {exception_id} successfully resolved.",
        "exception": target_exc
    }
