"""
Unit and Integration Tests for Bank Statement Parsers (CSV, MT940, CAMT.053).
"""

import pytest
from decimal import Decimal
from datetime import datetime

from backend.app.parsers.csv_parser import CSVParser
from backend.app.parsers.mt940_parser import MT940Parser
from backend.app.parsers.camt053_parser import CAMT053Parser
from backend.app.models.canonical import DirectionEnum


def test_csv_parser_valid_records():
    csv_data = """transaction_id,transaction_date,net_amount,currency,cr_dr,merchant_name,account_number,bank_ref_no,remarks,settlement_date
PB26031500000001,2026-03-15 10:30:00,1499.50,INR,CR,AMAZON PAY INDIA PVT LTD,98765432101,UTR001,UPI payment,2026-03-16
PB26031500000002,2026-03-15 11:15:00,2500.00,INR,DR,FLIPKART INTERNET,98765432102,UTR002,Refund debit,2026-03-16
"""
    parser = CSVParser()
    config = {
        "column_mappings": {
            "txn_id": "transaction_id",
            "txn_date": "transaction_date",
            "amount": "net_amount",
            "currency": "currency",
            "direction": "cr_dr",
            "counterparty_name": "merchant_name",
            "counterparty_account": "account_number",
            "bank_ref": "bank_ref_no",
            "narration": "remarks",
            "settlement_date": "settlement_date"
        }
    }
    result = parser.parse_content(csv_data, "test_hdfc.csv", "HDFC", config)
    assert result.successful_records == 2
    assert len(result.parse_errors) == 0
    assert result.transactions[0].txn_id == "PB26031500000001"
    assert result.transactions[0].amount == Decimal("1499.5000")
    assert result.transactions[0].direction == DirectionEnum.CR
    assert result.transactions[1].direction == DirectionEnum.DR


def test_mt940_parser_with_deviations():
    # MT940 with period decimals and non-standard tag 86
    mt940_data = """:20:AXIS20260315001
:25:910020030040050
:28C:00142/001
:60F:C260315INR50000000.00
:61:260315CN1499.50NTRFPB26031500000001//UTR001
:86:/NAME/AMAZON PAY INDIA PVT LTD/ACC/98765432101/REMK/UPI Payment
:62F:C260315INR50001499.50
"""
    parser = MT940Parser()
    result = parser.parse_content(mt940_data, "axis_mt940.sta", "AXIS")
    assert result.successful_records == 1
    txn = result.transactions[0]
    assert txn.amount == Decimal("1499.5000")
    assert txn.direction == DirectionEnum.CR
    assert "AMAZON" in txn.counterparty_name
    assert result.balances.opening_balance == Decimal("50000000.0000")
    assert result.balances.closing_balance == Decimal("50001499.5000")


def test_camt053_parser_xml():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
    <BkToCstmrStmt>
        <GrpHdr><MsgId>KOTAK-001</MsgId></GrpHdr>
        <Stmt>
            <Id>STMT-001</Id>
            <Acct><Id><IBAN>KKBK0002222987654321</IBAN></Id></Acct>
            <Bal>
                <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
                <Amt Ccy="INR">100000.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <Dt><Dt>2026-03-15</Dt></Dt>
            </Bal>
            <Ntry>
                <Amt Ccy="INR">2500.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <BookgDt><Dt>2026-03-15</Dt></BookgDt>
                <NtryDtls>
                    <TxDtls>
                        <Refs><EndToEndId>PB26031500000003</EndToEndId></Refs>
                        <RltdPties><Cdtr><Nm>ZOMATO ENTERPRISES</Nm></Cdtr></RltdPties>
                    </TxDtls>
                </NtryDtls>
            </Ntry>
            <Bal>
                <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
                <Amt Ccy="INR">102500.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <Dt><Dt>2026-03-15</Dt></Dt>
            </Bal>
        </Stmt>
    </BkToCstmrStmt>
</Document>"""
    parser = CAMT053Parser()
    result = parser.parse_content(xml_data, "kotak_camt.xml", "KOTAK")
    assert result.successful_records == 1
    assert result.transactions[0].txn_id == "PB26031500000003"
    assert result.transactions[0].amount == Decimal("2500.0000")
    assert result.balances.closing_balance == Decimal("102500.0000")
