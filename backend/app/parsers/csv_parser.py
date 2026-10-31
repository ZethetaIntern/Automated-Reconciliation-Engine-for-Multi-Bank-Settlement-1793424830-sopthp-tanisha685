"""
High-throughput streaming CSV parser.
Uses Python's standard csv module (memory-efficient O(1) space) and configurable bank mapping rules.
"""

import csv
import io
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from backend.app.parsers.base import BaseParser, ParseResult
from backend.app.models.canonical import SourceFormatEnum
from backend.app.normalisation.security import compute_sha256
from backend.app.normalisation.pipeline import normalise_transaction


class CSVParser(BaseParser):
    """
    Parses bank-specific CSV settlement files into canonical transaction objects.
    """

    def parse_content(
        self,
        content: str | bytes,
        filename: str,
        bank_code: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        if isinstance(content, bytes):
            file_sha256 = compute_sha256(content)
            # Try utf-8, fallback to latin-1
            try:
                text_stream = io.StringIO(content.decode("utf-8"))
            except UnicodeDecodeError:
                text_stream = io.StringIO(content.decode("latin-1", errors="replace"))
        else:
            file_sha256 = compute_sha256(content)
            text_stream = io.StringIO(content)

        cfg = config or {}
        mappings = cfg.get("column_mappings", {})
        delimiter = cfg.get("delimiter", ",")
        has_header = cfg.get("has_header", True)
        source_timezone = cfg.get("timezone", "Asia/Kolkata")

        transactions = []
        parse_errors = []
        line_num = 0

        # Sniff or standard reader
        reader = csv.reader(text_stream, delimiter=delimiter)

        headers = []
        if has_header:
            try:
                raw_headers = next(reader)
                line_num += 1
                headers = [h.strip().lower() for h in raw_headers]
            except StopIteration:
                return ParseResult(
                    transactions=[],
                    parse_errors=[{"line": 0, "error": "Empty CSV file"}],
                    total_records=0,
                    successful_records=0,
                    file_sha256=file_sha256
                )

        header_index_map = {h: idx for idx, h in enumerate(headers)}

        for row in reader:
            line_num += 1
            if not row or all(not cell.strip() for cell in row):
                continue

            try:
                raw_dict = {}

                if mappings:
                    for canon_key, col_spec in mappings.items():
                        val = None
                        if isinstance(col_spec, int):
                            if col_spec < len(row):
                                val = row[col_spec].strip()
                        elif isinstance(col_spec, str):
                            target_col = col_spec.lower()
                            if target_col in header_index_map:
                                idx = header_index_map[target_col]
                                if idx < len(row):
                                    val = row[idx].strip()
                        elif isinstance(col_spec, list):
                            # Combined columns (e.g. Axis splitting ref across col 4 and 5)
                            parts = []
                            for c in col_spec:
                                if isinstance(c, int) and c < len(row):
                                    parts.append(row[c].strip())
                                elif isinstance(c, str) and c.lower() in header_index_map:
                                    idx = header_index_map[c.lower()]
                                    if idx < len(row):
                                        parts.append(row[idx].strip())
                            val = " ".join([p for p in parts if p])
                        if val is not None:
                            raw_dict[canon_key] = val
                else:
                    # Fallback standard auto-header mapping
                    for h, idx in header_index_map.items():
                        if idx < len(row):
                            raw_dict[h] = row[idx].strip()

                # Normalise to canonical model
                canon_txn = normalise_transaction(
                    raw_data=raw_dict,
                    bank_code=bank_code,
                    source_format=SourceFormatEnum.CSV,
                    source_file=filename,
                    source_timezone=source_timezone
                )
                transactions.append(canon_txn)

            except Exception as e:
                parse_errors.append({
                    "line": line_num,
                    "row_content": row,
                    "error": str(e),
                    "exception_category": "FORMAT_ERROR"
                })

        return ParseResult(
            transactions=transactions,
            parse_errors=parse_errors,
            total_records=line_num - (1 if has_header else 0),
            successful_records=len(transactions),
            file_sha256=file_sha256,
            metadata={"bank_code": bank_code, "headers": headers}
        )
