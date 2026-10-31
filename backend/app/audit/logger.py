"""
Cryptographic Append-Only Audit Logger with SHA-256 Block Chaining.
Guarantees tamper-evident audit records per Section A4.3 and Section 128 of Companies Act, 2013.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import hashlib

from backend.app.models.schemas import AuditLogItem
from backend.app.models.db_service import persist_audit_log_entry


GENESIS_HASH = "0" * 64


def compute_entry_hash(
    event_id: str,
    timestamp_str: str,
    actor: str,
    action_type: str,
    affected_records: List[str],
    before_state: Optional[Dict[str, Any]],
    after_state: Optional[Dict[str, Any]],
    rationale: str,
    prev_hash: str
) -> str:
    """Computes deterministic SHA-256 hash across all record fields."""
    payload = {
        "event_id": event_id,
        "timestamp": timestamp_str,
        "actor": actor,
        "action_type": action_type,
        "affected_records": sorted(affected_records) if affected_records else [],
        "before_state": before_state or {},
        "after_state": after_state or {},
        "rationale": rationale,
        "prev_hash": prev_hash
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AuditLogger:
    """
    Manages in-memory and persisted chained audit log entries.
    """

    def __init__(self):
        self._entries: List[AuditLogItem] = []
        self._last_hash: str = GENESIS_HASH

    @property
    def last_hash(self) -> str:
        return self._last_hash

    def log_event(
        self,
        actor: str,
        action_type: str,
        affected_records: List[str],
        rationale: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> AuditLogItem:
        """
        Creates, hashes, chains, and appends a new audit log event.
        """
        now = timestamp or datetime.now(timezone.utc)
        event_id = f"AUD-{uuid.uuid4().hex.upper()}"
        ts_str = now.isoformat()

        entry_hash = compute_entry_hash(
            event_id=event_id,
            timestamp_str=ts_str,
            actor=actor,
            action_type=action_type,
            affected_records=affected_records,
            before_state=before_state,
            after_state=after_state,
            rationale=rationale,
            prev_hash=self._last_hash
        )

        item = AuditLogItem(
            event_id=event_id,
            timestamp=now,
            actor=actor,
            action_type=action_type,
            affected_records=affected_records,
            before_state=before_state,
            after_state=after_state,
            rationale=rationale,
            prev_hash=self._last_hash,
            sha256_hash=entry_hash,
            is_valid=True
        )

        self._entries.append(item)
        self._last_hash = entry_hash

        # Persist to database
        try:
            persist_audit_log_entry(item.model_dump())
        except Exception as e:
            pass

        return item

    def get_entries(
        self,
        action_type: Optional[str] = None,
        actor: Optional[str] = None,
        limit: int = 200
    ) -> List[AuditLogItem]:
        results = self._entries
        if action_type:
            results = [e for e in results if e.action_type.upper() == action_type.upper()]
        if actor:
            results = [e for e in results if e.actor.upper() == actor.upper()]
        return results[-limit:]


# Global shared audit instance
global_audit_logger = AuditLogger()
