"""
Unit tests for Cryptographic Audit Trail Chaining and Tamper Verification.
"""

from backend.app.audit.logger import AuditLogger
from backend.app.audit.verifier import verify_audit_chain


def test_audit_chain_integrity():
    logger = AuditLogger()

    # Log 3 sequential events
    e1 = logger.log_event("SYSTEM", "INGEST", ["TXN-1"], "Ingested file A")
    e2 = logger.log_event("MATCH_ENGINE", "MATCH", ["TXN-1", "EXT-1"], "Exact match")
    e3 = logger.log_event("ANALYST_1", "RESOLVE", ["EXC-1"], "Manual override")

    assert e2.prev_hash == e1.sha256_hash
    assert e3.prev_hash == e2.sha256_hash

    is_valid, violations = verify_audit_chain(logger._entries)
    assert is_valid is True
    assert len(violations) == 0


def test_audit_tamper_detection():
    logger = AuditLogger()
    e1 = logger.log_event("SYSTEM", "INGEST", ["TXN-1"], "Ingested file")
    e2 = logger.log_event("MATCH_ENGINE", "MATCH", ["TXN-1"], "Matched")

    # Deliberately tamper with entry 1 rationale
    e1.rationale = "TAMPERED_FRAUDULENT_TEXT"

    is_valid, violations = verify_audit_chain(logger._entries)
    assert is_valid is False
    assert len(violations) > 0
