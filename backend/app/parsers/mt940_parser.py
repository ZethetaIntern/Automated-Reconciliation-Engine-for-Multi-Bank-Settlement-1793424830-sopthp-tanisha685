"""
State-machine parser for SWIFT MT940 messages.
Handles standard specification and 5 common bank deviations:
1. Period decimal separator vs comma.
2. Missing funds code in :61: line.
3. Variable / non-standard :86: sub-fields.
4. Extended reference strings in :61:.
5. Multi-line continuations across all tags.
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date, timezone
from decimal import Decimal

from backend.app.parsers.base import BaseParser, ParseResult, BalanceReport
from backend.app.models.canonical import CanonicalTransaction, DirectionEnum, SourceFormatEnum
from backend.app.normalisation.security import compute_sha256
from backend.app.normalisation.currency import validate_and_format_amount
from backend.app.normalisation.pipeline import clean_reference, clean_counterparty, mask_pan
from backend.app.normalisation.timezone import normalise_to_utc


# Regex for field tags: e.g. :20:, :25:, :28C:, :60F:, :60M:, :61:, :86:, :62F:, :62M:
TAG_REGEX = re.compile(r"^:([0-9]{2}[A-Z]?):(.*)$")

# Regex for Balance fields (:60F:, :62F:, etc.): (C/D)(YYMMDD)(3-char currency)(amount)
BALANCE_REGEX = re.compile(r"^([CD])(\d{6})([A-Z]{3})([0-9,.]+)")


class MT940Parser(BaseParser):
    """
    Robust state-machine parser for SWIFT MT940 messages.
    """

    def _parse_balance_field(self, raw_str: str) -> Tuple[Optional[Decimal], Optional[str], str, str]:
        """Extracts (amount, date_str, currency, direction) from balance field like C260315INR1250000,50"""
        match = BALANCE_REGEX.match(raw_str.strip())
        if match:
            direction_mark, date_str, ccy, amt_str = match.groups()
            amt_clean = amt_str.replace(",", ".")
            amt = validate_and_format_amount(amt_clean)
            if direction_mark == "D":
                amt = -amt
            return amt, date_str, ccy, direction_mark
        return None, None, "INR", "C"

    def _parse_tag_61(self, line: str) -> Dict[str, Any]:
        """
        Parses tag :61: statement line.
        Handles missing funds code, period/comma decimals, extended references.
        Standard format: 6!n[4!n]2a[1!a]15d1a3c16x[//16x]
        """
        clean = line.strip()
        result = {
            "value_date_raw": "",
            "entry_date_raw": "",
            "direction": "CR",
            "amount": Decimal("0.00"),
            "txn_type": "N",
            "id_code": "TRF",
            "reference": "",
            "supp_details": ""
        }

        if len(clean) < 10:
            return result

        # 1. Value Date: 6 digits YYMMDD
        val_date_str = clean[:6]
        result["value_date_raw"] = val_date_str
        pos = 6

        # 2. Optional Entry Date: 4 digits MMDD (if followed immediately by D/C/RC/RD)
        if clean[pos:pos+4].isdigit() and clean[pos+4:pos+6].upper() in ("CR", "DR", "RC", "RD", "C", "D"):
            result["entry_date_raw"] = clean[pos:pos+4]
            pos += 4

        # 3. Debit / Credit Mark: D, C, RC, RD
        direction_mark = "CR"
        if clean[pos:pos+2].upper() in ("RC", "RD"):
            direction_mark = "CR" if clean[pos:pos+2].upper() == "RC" else "DR"
            pos += 2
        elif clean[pos:pos+1].upper() in ("C", "D"):
            direction_mark = "CR" if clean[pos:pos+1].upper() == "C" else "DR"
            pos += 1
        result["direction"] = direction_mark

        # 4. Optional Funds Code: 1 character letter before the amount digits
        if pos < len(clean) and clean[pos].isalpha() and pos + 1 < len(clean) and clean[pos+1].isdigit():
            funds_code = clean[pos]
            pos += 1

        # 5. Amount: numeric with comma or period decimal separator
        amt_match = re.match(r"^([0-9]+[.,]?[0-9]*)", clean[pos:])
        if amt_match:
            raw_amt_str = amt_match.group(1)
            pos += len(raw_amt_str)
            result["amount"] = validate_and_format_amount(raw_amt_str.replace(",", "."))

        # 6. Transaction type code (S, N, F) + 3 char ID code + Reference
        remaining = clean[pos:].strip()
        if remaining.startswith("//"):
            # Swift supplementary reference
            result["reference"] = remaining[2:].strip()
        else:
            # Type code + ref
            parts = remaining.split("//", 1)
            main_ref_part = parts[0]
            if len(main_ref_part) >= 4 and main_ref_part[0].isalpha() and main_ref_part[1:4].isalpha():
                result["txn_type"] = main_ref_part[0]
                result["id_code"] = main_ref_part[1:4]
                result["reference"] = main_ref_part[4:].strip()
            else:
                result["reference"] = main_ref_part.strip()

            if len(parts) > 1:
                result["supp_details"] = parts[1].strip()
                if not result["reference"]:
                    result["reference"] = parts[1].strip()

        return result

    def _parse_tag_86(self, raw_86: str) -> Tuple[str, str, str]:
        """
        Parses :86: unstructured / structured narrative.
        Extracts (counterparty_name, counterparty_account, narration).
        Supports subfield tags e.g. ?20, /TRN/, /NAME/, /ACC/, /REMK/ or free-text lines.
        """
        if not raw_86:
            return "", "", ""

        lines = [l.strip() for l in raw_86.splitlines() if l.strip()]
        full_text = " ".join(lines)

        cp_name = ""
        cp_acct = ""
        narration = full_text

        # Check for structured tags like /NAME/, /ACC/, /REMK/ or ?20, ?21
        name_match = re.search(r"/(?:NAME|BNF|CDTR)/([^/]+)", full_text, re.IGNORECASE)
        acct_match = re.search(r"/(?:ACC|IBAN|ACCT)/([^/]+)", full_text, re.IGNORECASE)

        if name_match:
            cp_name = name_match.group(1).strip()
        if acct_match:
            cp_acct = acct_match.group(1).strip()

        if not cp_name and lines:
            cp_name = lines[0][:140]
        if not cp_acct and len(lines) > 1:
            # Check if line 2 contains account/IBAN pattern
            acct_cand = re.search(r"\b[A-Z0-9]{9,34}\b", lines[1])
            if acct_cand:
                cp_acct = acct_cand.group(0)

        return cp_name, cp_acct, narration

    def parse_content(
        self,
        content: str | bytes,
        filename: str,
        bank_code: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        if isinstance(content, bytes):
            file_sha256 = compute_sha256(content)
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="replace")
        else:
            file_sha256 = compute_sha256(content)
            text = content

        cfg = config or {}
        source_tz = cfg.get("timezone", "Asia/Kolkata")
        bank_ccy = cfg.get("currency", "INR")

        transactions: List[CanonicalTransaction] = []
        parse_errors: List[Dict[str, Any]] = []

        # Parse tags using state machine
        current_tag = None
        current_content: List[str] = []
        tagged_blocks: List[Tuple[str, str]] = []

        for line in text.splitlines():
            line_str = line.strip("\r\n")
            match = TAG_REGEX.match(line_str)
            if match:
                if current_tag is not None:
                    tagged_blocks.append((current_tag, "\n".join(current_content)))
                current_tag = match.group(1)
                current_content = [match.group(2).strip()]
            else:
                if current_tag is not None:
                    current_content.append(line_str)

        if current_tag is not None:
            tagged_blocks.append((current_tag, "\n".join(current_content)))

        # Process statements
        statement_ref = ""
        account_id = ""
        statement_num = ""
        opening_bal: Optional[Decimal] = None
        opening_bal_date = None
        closing_bal: Optional[Decimal] = None
        closing_bal_date = None
        statement_currency = bank_ccy

        pending_61_data: Optional[Dict[str, Any]] = None

        def _flush_transaction(t61_data: Dict[str, Any], t86_text: str):
            if not t61_data:
                return
            try:
                # Parse date YYMMDD
                val_date_str = t61_data["value_date_raw"]
                if len(val_date_str) == 6 and val_date_str.isdigit():
                    yy = 2000 + int(val_date_str[0:2])
                    mm = int(val_date_str[2:4])
                    dd = int(val_date_str[4:6])
                    txn_dt = datetime(yy, mm, dd, 12, 0, 0)
                else:
                    txn_dt = datetime.now(timezone.utc)

                utc_dt, _ = normalise_to_utc(txn_dt, source_tz)

                cp_name, cp_acct, raw_narration = self._parse_tag_86(t86_text)
                clean_cp_name = clean_counterparty(cp_name)
                ref = t61_data["reference"] or t61_data.get("supp_details") or statement_ref

                # Mask PAN
                masked_narration, m1 = mask_pan(raw_narration)
                masked_ref, m2 = mask_pan(clean_reference(ref))
                masked_cp_acct, m3 = mask_pan(cp_acct)

                txn = CanonicalTransaction(
                    txn_id=masked_ref or f"MT940-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                    txn_date=utc_dt,
                    amount=t61_data["amount"],
                    currency=statement_currency,
                    direction=DirectionEnum.CR if t61_data["direction"] == "CR" else DirectionEnum.DR,
                    counterparty_name=clean_cp_name,
                    counterparty_account=masked_cp_acct,
                    bank_ref=masked_ref,
                    narration=masked_narration,
                    settlement_date=utc_dt.date(),
                    source_format=SourceFormatEnum.MT940,
                    source_file=filename,
                    bank_code=bank_code.upper(),
                    raw_payload=t61_data,
                    is_masked=m1 or m2 or m3
                )
                transactions.append(txn)
            except Exception as e:
                parse_errors.append({
                    "tag": ":61:",
                    "data": t61_data,
                    "error": str(e),
                    "exception_category": "FORMAT_ERROR"
                })

        for tag, val in tagged_blocks:
            if tag == "20":
                statement_ref = val.strip()
            elif tag == "25":
                account_id = val.strip()
            elif tag in ("28", "28C"):
                statement_num = val.strip()
            elif tag in ("60F", "60M"):
                amt, dt_str, ccy, _ = self._parse_balance_field(val)
                opening_bal = amt
                opening_bal_date = dt_str
                statement_currency = ccy or statement_currency
            elif tag == "61":
                # Flush previous transaction if one was waiting without an :86:
                if pending_61_data:
                    _flush_transaction(pending_61_data, "")
                pending_61_data = self._parse_tag_61(val)
            elif tag == "86":
                if pending_61_data:
                    _flush_transaction(pending_61_data, val)
                    pending_61_data = None
            elif tag in ("62F", "62M"):
                if pending_61_data:
                    _flush_transaction(pending_61_data, "")
                    pending_61_data = None
                amt, dt_str, ccy, _ = self._parse_balance_field(val)
                closing_bal = amt
                closing_bal_date = dt_str

        if pending_61_data:
            _flush_transaction(pending_61_data, "")

        balances = BalanceReport(
            opening_balance=opening_bal,
            opening_balance_date=opening_bal_date,
            closing_balance=closing_bal,
            closing_balance_date=closing_bal_date,
            currency=statement_currency,
            account_number=account_id,
            statement_number=statement_num
        )

        return ParseResult(
            transactions=transactions,
            parse_errors=parse_errors,
            total_records=len(transactions) + len(parse_errors),
            successful_records=len(transactions),
            file_sha256=file_sha256,
            balances=balances,
            metadata={
                "bank_code": bank_code,
                "statement_ref": statement_ref,
                "account_id": account_id,
                "statement_num": statement_num
            }
        )
