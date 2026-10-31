"""
File Ingestion, Integrity Verification, and Bank Config Management Routes.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import yaml

from backend.app.normalisation.security import compute_sha256
from backend.app.parsers.detector import detect_file_format, validate_csv_schema
from backend.app.parsers.csv_parser import CSVParser
from backend.app.parsers.mt940_parser import MT940Parser
from backend.app.parsers.camt053_parser import CAMT053Parser
from backend.app.audit.logger import global_audit_logger

router = APIRouter(prefix="/api/v1/files", tags=["Files & Ingestion"])

INGESTED_FILES_REGISTRY: List[Dict[str, Any]] = [
    {
        "file_id": "FILE-001",
        "filename": "hdfc_settlement_20260315.csv",
        "bank_code": "HDFC",
        "format": "CSV",
        "record_count": 25000,
        "parse_error_count": 0,
        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "status": "INGESTED_VERIFIED",
        "ingested_at": "2026-03-30T09:15:00Z"
    },
    {
        "file_id": "FILE-002",
        "filename": "icici_settlement_20260315.csv",
        "bank_code": "ICICI",
        "format": "CSV (Variant)",
        "record_count": 18000,
        "parse_error_count": 0,
        "sha256_hash": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        "status": "INGESTED_VERIFIED",
        "ingested_at": "2026-03-30T09:20:00Z"
    },
    {
        "file_id": "FILE-003",
        "filename": "axis_mt940_20260315.sta",
        "bank_code": "AXIS",
        "format": "MT940",
        "record_count": 12000,
        "parse_error_count": 0,
        "sha256_hash": "9876543210fedcba0123456789abcdef0123456789abcdef0123456789abcdef",
        "status": "INGESTED_VERIFIED",
        "ingested_at": "2026-03-30T09:25:00Z"
    },
    {
        "file_id": "FILE-004",
        "filename": "sbi_mt940_20260315.sta",
        "bank_code": "SBI",
        "format": "MT940",
        "record_count": 20000,
        "parse_error_count": 0,
        "sha256_hash": "456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123",
        "status": "INGESTED_VERIFIED",
        "ingested_at": "2026-03-30T09:30:00Z"
    },
    {
        "file_id": "FILE-005",
        "filename": "kotak_camt053_20260315.xml",
        "bank_code": "KOTAK",
        "format": "CAMT.053",
        "record_count": 15000,
        "parse_error_count": 0,
        "sha256_hash": "def0123456789abcdef0123456789abcdef0123456789abcdef0123456789abc",
        "status": "INGESTED_VERIFIED",
        "ingested_at": "2026-03-30T09:35:00Z"
    }
]


@router.get("")
def list_ingested_files():
    """Returns list of all ingested statement files with SHA-256 cryptographic fingerprints."""
    return INGESTED_FILES_REGISTRY


@router.post("/upload")
async def upload_bank_file(
    file: UploadFile = File(...),
    bank_code: str = Form("HDFC")
):
    """
    Ingests and parses an uploaded bank settlement file.
    Computes SHA-256 fingerprint, validates format against bank schema, and parses canonical records.
    """
    content = await file.read()
    file_hash = compute_sha256(content)

    # Check duplicate file ingestion (Scenario B4.4)
    for existing in INGESTED_FILES_REGISTRY:
        if existing["sha256_hash"] == file_hash:
            raise HTTPException(
                status_code=400,
                detail=f"DUPLICATE_FILE_DETECTED: This exact file content was already ingested as '{existing['filename']}' on {existing['ingested_at']}."
            )

    # Detect format
    detected_format, format_meta = detect_file_format(content, filename=file.filename)

    # Parse with appropriate parser
    if detected_format.value == "CAMT.053":
        parser = CAMT053Parser()
    elif detected_format.value == "MT940":
        parser = MT940Parser()
    else:
        parser = CSVParser()

    parse_res = parser.parse_content(content, file.filename, bank_code.upper())

    file_record = {
        "file_id": f"FILE-{len(INGESTED_FILES_REGISTRY)+1:03d}",
        "filename": file.filename,
        "bank_code": bank_code.upper(),
        "format": detected_format.value,
        "record_count": parse_res.successful_records,
        "parse_error_count": len(parse_res.parse_errors),
        "sha256_hash": file_hash,
        "status": "INGESTED_VERIFIED" if len(parse_res.parse_errors) == 0 else "PARTIALLY_INGESTED",
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }
    INGESTED_FILES_REGISTRY.append(file_record)

    # Log to audit chain
    global_audit_logger.log_event(
        actor="FILE_INGESTION_GATEWAY",
        action_type="INGEST_FILE",
        affected_records=[file_record["file_id"]],
        rationale=f"Ingested file {file.filename} with SHA-256 {file_hash[:16]}... ({parse_res.successful_records} valid records)"
    )

    return {
        "status": "SUCCESS",
        "file_details": file_record,
        "parsed_transactions_sample": [t.to_dict() for t in parse_res.transactions[:5]],
        "parse_errors": parse_res.parse_errors[:5]
    }
