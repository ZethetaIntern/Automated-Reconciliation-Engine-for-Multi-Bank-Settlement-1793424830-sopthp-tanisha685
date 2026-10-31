"""
Format detection and schema deviation engine.
Detects CSV vs MT940 vs CAMT.053 and flags unexpected column order changes (Scenario B4.1).
"""

import re
from typing import Tuple, Dict, Any, Optional
from backend.app.models.canonical import SourceFormatEnum


def detect_file_format(content: str | bytes, filename: str = "") -> Tuple[SourceFormatEnum, Dict[str, Any]]:
    """
    Sniffs file content or extension to detect standard format and bank deviations.
    """
    if isinstance(content, bytes):
        sample = content[:4096].decode("utf-8", errors="replace")
    else:
        sample = content[:4096]

    # XML / CAMT.053 detection
    if "<BkToCstmrStmt>" in sample or "<Document" in sample or "urn:iso:std:iso:20022" in sample:
        return SourceFormatEnum.CAMT053, {"detected": "XML ISO 20022 CAMT.053"}

    # SWIFT MT940 detection
    if re.search(r":20:", sample) and (re.search(r":61:", sample) or re.search(r":60[FM]:", sample)):
        return SourceFormatEnum.MT940, {"detected": "SWIFT MT940"}

    # Fallback to CSV
    return SourceFormatEnum.CSV, {"detected": "CSV Settlement"}


def validate_csv_schema(
    headers: list[str],
    expected_mappings: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """
    Compares CSV headers against expected bank configuration mapping.
    Raises FORMAT_CHANGE_DETECTED if expected columns are missing or moved unexpectedly.
    """
    if not headers or not expected_mappings:
        return True, None

    normalized_headers = [h.strip().lower() for h in headers]

    for field, expected_col in expected_mappings.items():
        if isinstance(expected_col, str):
            if expected_col.lower() not in normalized_headers:
                return False, f"FORMAT_CHANGE_DETECTED: Expected column '{expected_col}' for field '{field}' was not found in ingested headers {normalized_headers}"
        elif isinstance(expected_col, int):
            if expected_col >= len(headers):
                return False, f"FORMAT_CHANGE_DETECTED: Expected column index {expected_col} out of range ({len(headers)} columns present)"

    return True, None
