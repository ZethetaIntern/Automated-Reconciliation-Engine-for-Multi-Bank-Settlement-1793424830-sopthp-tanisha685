"""
Normalisation Pipeline for Canonical Data Model.
Executes chain: timezone_normalise() -> currency_normalise() -> reference_clean() -> amount_standardise() -> counterparty_clean() -> pan_mask().
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.app.models.canonical import CanonicalTransaction, DirectionEnum, SourceFormatEnum
from backend.app.normalisation.timezone import normalise_to_utc
from backend.app.normalisation.currency import validate_and_format_amount
from backend.app.normalisation.security import mask_pan


ABBREVIATIONS_MAP = {
    r"\bP\.?L\.?T\.?D\.?\b": "PVT LTD",
    r"\bPVT\.?\s*LTD\.?\b": "PVT LTD",
    r"\bPRIVATE\s+LIMITED\b": "PVT LTD",
    r"\bL\.?T\.?D\.?\b": "LTD",
    r"\bLIMITED\b": "LTD",
    r"\bCORP\.?\b": "CORPORATION",
    r"\bINC\.?\b": "INCORPORATED",
    r"\bLLP\b": "LLP",
    r"\bTECH\.?\b": "TECHNOLOGIES",
}


def clean_reference(ref: Optional[str]) -> str:
    """Strip extraneous whitespace, dashes, leading/trailing symbols, and uppercase."""
    if not ref:
        return ""
    s = str(ref).strip().upper()
    # Remove excessive punctuation but keep valid alpha-numeric chars and essential dashes
    s = re.sub(r"[\t\r\n]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def clean_counterparty(name: Optional[str]) -> str:
    """Normalises counterparty names, standardises company abbreviations."""
    if not name:
        return ""
    s = str(name).strip().upper()
    for pat, rep in ABBREVIATIONS_MAP.items():
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)
    # Remove multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalise_transaction(
    raw_data: Dict[str, Any],
    bank_code: str = "INTERNAL",
    source_format: SourceFormatEnum = SourceFormatEnum.CSV,
    source_file: str = "",
    source_timezone: str = "Asia/Kolkata"
) -> CanonicalTransaction:
    """
    Transforms raw dictionary input into a strictly validated CanonicalTransaction.
    """
    raw_id = str(raw_data.get("txn_id") or raw_data.get("transaction_id") or raw_data.get("ref_no") or "").strip()
    raw_bank_ref = str(raw_data.get("bank_ref") or raw_data.get("utr") or raw_data.get("reference") or "").strip()
    
    # If txn_id is empty, use bank_ref or fallback
    txn_id = raw_id if raw_id else (raw_bank_ref if raw_bank_ref else f"TXN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")

    # Parse and normalise timestamp to UTC
    raw_date = raw_data.get("txn_date") or raw_data.get("date") or raw_data.get("booking_date") or datetime.now(timezone.utc)
    if isinstance(raw_date, str):
        from dateutil.parser import parse as parse_date
        try:
            parsed_dt = parse_date(raw_date)
        except Exception:
            parsed_dt = datetime.now(timezone.utc)
    elif isinstance(raw_date, datetime):
        parsed_dt = raw_date
    else:
        parsed_dt = datetime.now(timezone.utc)

    utc_dt, _ = normalise_to_utc(parsed_dt, source_timezone)

    # Standardise amount
    amount_dec = validate_and_format_amount(raw_data.get("amount", 0))

    # Standardise direction
    raw_dir = str(raw_data.get("direction") or raw_data.get("type") or raw_data.get("dr_cr") or "CR").strip().upper()
    direction = DirectionEnum.CR if raw_dir in ("CR", "C", "CREDIT", "RC") else DirectionEnum.DR

    # Currency
    curr = str(raw_data.get("currency") or "INR").strip().upper()
    if len(curr) != 3:
        curr = "INR"

    # Counterparty and Narration
    cp_name = clean_counterparty(raw_data.get("counterparty_name") or raw_data.get("party_name") or raw_data.get("beneficiary") or "")
    cp_acct = str(raw_data.get("counterparty_account") or raw_data.get("account_number") or raw_data.get("iban") or "").strip()
    narration = str(raw_data.get("narration") or raw_data.get("remarks") or raw_data.get("description") or "").strip()

    # Mask PAN if present in narration, reference, or counterparty account
    masked_narration, masked_1 = mask_pan(narration)
    masked_ref, masked_2 = mask_pan(clean_reference(raw_bank_ref))
    masked_cp_acct, masked_3 = mask_pan(cp_acct)
    is_masked = masked_1 or masked_2 or masked_3

    # Settlement date
    settlement_date_val = raw_data.get("settlement_date")
    if isinstance(settlement_date_val, str):
        try:
            from dateutil.parser import parse as parse_date
            settlement_date_val = parse_date(settlement_date_val).date()
        except Exception:
            settlement_date_val = utc_dt.date()
    elif isinstance(settlement_date_val, datetime):
        settlement_date_val = settlement_date_val.date()
    elif settlement_date_val is None:
        settlement_date_val = utc_dt.date()

    return CanonicalTransaction(
        txn_id=clean_reference(txn_id),
        txn_date=utc_dt,
        amount=amount_dec,
        currency=curr,
        direction=direction,
        counterparty_name=cp_name,
        counterparty_account=masked_cp_acct,
        bank_ref=masked_ref,
        narration=masked_narration,
        settlement_date=settlement_date_val,
        source_format=source_format,
        source_file=source_file,
        bank_code=bank_code.upper(),
        raw_payload=raw_data,
        is_masked=is_masked
    )
