"""
ISO 20022 CAMT.053 XML Statement Parser.
Extracts nested Ntry and TxDtls elements, handles XML namespaces, and extracts both
transaction items and statement balances (Closing Booked CLBD vs Closing Available CLAV).
"""

import io
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timezone
from decimal import Decimal
from lxml import etree

from backend.app.parsers.base import BaseParser, ParseResult, BalanceReport
from backend.app.models.canonical import CanonicalTransaction, DirectionEnum, SourceFormatEnum
from backend.app.normalisation.security import compute_sha256, mask_pan
from backend.app.normalisation.currency import validate_and_format_amount
from backend.app.normalisation.pipeline import clean_reference, clean_counterparty
from backend.app.normalisation.timezone import normalise_to_utc


class CAMT053Parser(BaseParser):
    """
    Parser for ISO 20022 CAMT.053 XML messages.
    """

    def parse_content(
        self,
        content: str | bytes,
        filename: str,
        bank_code: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        file_sha256 = compute_sha256(content_bytes)
        cfg = config or {}
        source_tz = cfg.get("timezone", "Asia/Kolkata")
        bank_ccy = cfg.get("currency", "INR")

        transactions: List[CanonicalTransaction] = []
        parse_errors: List[Dict[str, Any]] = []

        try:
            tree = etree.fromstring(content_bytes)
        except Exception as e:
            return ParseResult(
                transactions=[],
                parse_errors=[{"error": f"Invalid XML format: {str(e)}", "exception_category": "FORMAT_ERROR"}],
                total_records=0,
                successful_records=0,
                file_sha256=file_sha256
            )

        # Helper to find elements ignoring namespaces
        def _find_tag(elem, tag_name):
            for child in elem:
                local_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if local_tag == tag_name:
                    return child
            return None

        def _find_all_tags(elem, tag_name):
            results = []
            for child in elem:
                local_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if local_tag == tag_name:
                    results.append(child)
            return results

        def _text(elem, tag_name, default=""):
            child = _find_tag(elem, tag_name)
            return child.text.strip() if (child is not None and child.text) else default

        # 1. Header & Statement info
        grp_hdr = _find_tag(tree, "GrpHdr")
        msg_id = _text(grp_hdr, "MsgId", "") if grp_hdr is not None else ""

        stmts = _find_all_tags(tree, "Stmt")
        if not stmts:
            # Check root BkToCstmrStmt wrapper
            root_stmt = _find_tag(tree, "BkToCstmrStmt")
            if root_stmt is not None:
                stmts = _find_all_tags(root_stmt, "Stmt")

        opening_bal: Optional[Decimal] = None
        opening_bal_date = None
        closing_bal: Optional[Decimal] = None
        closing_bal_date = None
        account_number = ""

        for stmt in stmts:
            # Account ID
            acct_elem = _find_tag(stmt, "Acct")
            if acct_elem is not None:
                id_elem = _find_tag(acct_elem, "Id")
                if id_elem is not None:
                    account_number = _text(id_elem, "IBAN") or _text(id_elem, "Othr")

            # Extract balances (OPBD, CLBD, CLAV)
            bal_elems = _find_all_tags(stmt, "Bal")
            for b in bal_elems:
                tp_elem = _find_tag(b, "Tp")
                type_code = ""
                if tp_elem is not None:
                    cd_or_prtry = _find_tag(tp_elem, "CdOrPrtry")
                    if cd_or_prtry is not None:
                        type_code = _text(cd_or_prtry, "Cd")
                
                amt_elem = _find_tag(b, "Amt")
                amt_val = validate_and_format_amount(amt_elem.text if (amt_elem is not None and amt_elem.text) else "0")
                cdt_dbt = _text(b, "CdtDbtInd", "CR")
                if cdt_dbt in ("DBIT", "DR"):
                    amt_val = -amt_val

                dt_elem = _find_tag(b, "Dt")
                dt_str = ""
                if dt_elem is not None:
                    dt_str = _text(dt_elem, "Dt") or _text(dt_elem, "DtTm")

                if type_code in ("OPBD", "PRCD"):
                    opening_bal = amt_val
                    opening_bal_date = dt_str
                elif type_code in ("CLBD", "CLAV"):
                    closing_bal = amt_val
                    closing_bal_date = dt_str

            # Parse entries <Ntry>
            ntry_elems = _find_all_tags(stmt, "Ntry")
            for ntry in ntry_elems:
                try:
                    # Amount and currency
                    amt_elem = _find_tag(ntry, "Amt")
                    amt_str = amt_elem.text if (amt_elem is not None and amt_elem.text) else "0"
                    ccy = amt_elem.attrib.get("Ccy", bank_ccy) if amt_elem is not None else bank_ccy
                    amt_dec = validate_and_format_amount(amt_str)

                    # Direction
                    cdt_dbt = _text(ntry, "CdtDbtInd", "CR")
                    direction = DirectionEnum.CR if cdt_dbt in ("CRDT", "CR") else DirectionEnum.DR

                    # Booking / Value date
                    bookg_dt = _find_tag(ntry, "BookgDt")
                    val_dt = _find_tag(ntry, "ValDt")
                    raw_dt_str = ""
                    if bookg_dt is not None:
                        raw_dt_str = _text(bookg_dt, "Dt") or _text(bookg_dt, "DtTm")
                    elif val_dt is not None:
                        raw_dt_str = _text(val_dt, "Dt") or _text(val_dt, "DtTm")

                    if raw_dt_str:
                        from dateutil.parser import parse as parse_date
                        try:
                            parsed_dt = parse_date(raw_dt_str)
                        except Exception:
                            parsed_dt = datetime.now(timezone.utc)
                    else:
                        parsed_dt = datetime.now(timezone.utc)

                    utc_dt, _ = normalise_to_utc(parsed_dt, source_tz)

                    # Additional Entry Info / Narration
                    addtl_info = _text(ntry, "AddtlNtryInf", "")

                    # Check nested NtryDtls -> TxDtls
                    ntry_dtls = _find_all_tags(ntry, "NtryDtls")
                    tx_found = False

                    for nd in ntry_dtls:
                        tx_dtls = _find_all_tags(nd, "TxDtls")
                        for tx in tx_dtls:
                            tx_found = True
                            refs_elem = _find_tag(tx, "Refs")
                            end_to_end_id = ""
                            tx_id = ""
                            instr_id = ""
                            if refs_elem is not None:
                                end_to_end_id = _text(refs_elem, "EndToEndId")
                                tx_id = _text(refs_elem, "TxId")
                                instr_id = _text(refs_elem, "InstrId")

                            # Parties
                            rltd_pties = _find_tag(tx, "RltdPties")
                            cp_name = ""
                            cp_acct = ""
                            if rltd_pties is not None:
                                # If credit, look for Debtor, if debit look for Creditor
                                if direction == DirectionEnum.CR:
                                    party = _find_tag(rltd_pties, "Dbtr")
                                    if party is None:
                                        party = _find_tag(rltd_pties, "Cdtr")
                                    party_acct = _find_tag(rltd_pties, "DbtrAcct")
                                    if party_acct is None:
                                        party_acct = _find_tag(rltd_pties, "CdtrAcct")
                                else:
                                    party = _find_tag(rltd_pties, "Cdtr")
                                    if party is None:
                                        party = _find_tag(rltd_pties, "Dbtr")
                                    party_acct = _find_tag(rltd_pties, "CdtrAcct")
                                    if party_acct is None:
                                        party_acct = _find_tag(rltd_pties, "DbtrAcct")

                                if party is not None:
                                    cp_name = _text(party, "Nm")
                                if party_acct is not None:
                                    p_id = _find_tag(party_acct, "Id")
                                    if p_id is not None:
                                        cp_acct = _text(p_id, "IBAN") or _text(p_id, "Othr")

                            # Remittance info
                            rmt_inf = _find_tag(tx, "RmtInf")
                            tx_narration = addtl_info
                            if rmt_inf is not None:
                                ustrd = _text(rmt_inf, "Ustrd")
                                if ustrd:
                                    tx_narration = f"{addtl_info} {ustrd}".strip()

                            final_ref = end_to_end_id or tx_id or instr_id or msg_id
                            clean_cp = clean_counterparty(cp_name)
                            masked_narration, m1 = mask_pan(tx_narration)
                            masked_ref, m2 = mask_pan(clean_reference(final_ref))
                            masked_acct, m3 = mask_pan(cp_acct)

                            txn = CanonicalTransaction(
                                txn_id=masked_ref or f"CAMT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                                txn_date=utc_dt,
                                amount=amt_dec,
                                currency=ccy,
                                direction=direction,
                                counterparty_name=clean_cp,
                                counterparty_account=masked_acct,
                                bank_ref=masked_ref,
                                narration=masked_narration,
                                settlement_date=utc_dt.date(),
                                source_format=SourceFormatEnum.CAMT053,
                                source_file=filename,
                                bank_code=bank_code.upper(),
                                raw_payload={"msg_id": msg_id, "end_to_end_id": end_to_end_id},
                                is_masked=m1 or m2 or m3
                            )
                            transactions.append(txn)

                    if not tx_found:
                        # Direct entry level transaction
                        clean_ref = clean_reference(msg_id)
                        masked_narration, m1 = mask_pan(addtl_info)
                        masked_ref, m2 = mask_pan(clean_ref)

                        txn = CanonicalTransaction(
                            txn_id=masked_ref or f"CAMT-ENTRY-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
                            txn_date=utc_dt,
                            amount=amt_dec,
                            currency=ccy,
                            direction=direction,
                            counterparty_name="",
                            counterparty_account="",
                            bank_ref=masked_ref,
                            narration=masked_narration,
                            settlement_date=utc_dt.date(),
                            source_format=SourceFormatEnum.CAMT053,
                            source_file=filename,
                            bank_code=bank_code.upper(),
                            raw_payload={"msg_id": msg_id},
                            is_masked=m1 or m2
                        )
                        transactions.append(txn)

                except Exception as e:
                    parse_errors.append({
                        "error": str(e),
                        "exception_category": "FORMAT_ERROR"
                    })

        balances = BalanceReport(
            opening_balance=opening_bal,
            opening_balance_date=opening_bal_date,
            closing_balance=closing_bal,
            closing_balance_date=closing_bal_date,
            currency=bank_ccy,
            account_number=account_number,
            statement_number=msg_id
        )

        return ParseResult(
            transactions=transactions,
            parse_errors=parse_errors,
            total_records=len(transactions) + len(parse_errors),
            successful_records=len(transactions),
            file_sha256=file_sha256,
            balances=balances,
            metadata={"msg_id": msg_id, "account_number": account_number}
        )
