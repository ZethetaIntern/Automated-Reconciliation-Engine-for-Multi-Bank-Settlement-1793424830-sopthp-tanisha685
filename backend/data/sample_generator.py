"""
Synthetic Financial Data Generator.
Generates all 7 datasets specified in Section D10 with planted exceptions and sealed manifest.
"""

import os
import json
import csv
import random
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

# Seed for deterministic generation per Section A8.1
random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "generated")
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except (OSError, PermissionError):
    DATA_DIR = "/tmp/generated"
    os.makedirs(DATA_DIR, exist_ok=True)

MERCHANTS = [
    ("MERCH-001", "AMAZON PAY INDIA PVT LTD", "HDFC0001234", "98765432101"),
    ("MERCH-002", "FLIPKART INTERNET PRIVATE LIMITED", "ICIC0005678", "98765432102"),
    ("MERCH-003", "ZOMATO ENTERPRISES LTD", "UTIB0009999", "98765432103"),
    ("MERCH-004", "SWIGGY BUNDL TECHNOLOGIES", "SBIN0001111", "98765432104"),
    ("MERCH-005", "RELIANCE RETAIL LIMITED", "KKBK0002222", "98765432105"),
    ("MERCH-006", "TATA DIGITAL PRIVATE LIMITED", "YESB0003333", "98765432106"),
    ("MERCH-007", "MAKEMYTRIP INDIA PVT LTD", "INDB0004444", "98765432107"),
    ("MERCH-008", "BOOKMYSHOW BIGTREE ENT", "HDFC0001234", "98765432108"),
    ("MERCH-009", "ZEPTO QUICK COMMERCE", "ICIC0005678", "98765432109"),
    ("MERCH-010", "BLINKIT COMMERCE PVT LTD", "UTIB0009999", "98765432110"),
]


def generate_all_datasets(scale_factor: float = 0.05):
    """
    Generates realistic multi-bank financial transaction data.
    Default scale_factor generates ~10,000 internal records for instant local loading and testing.
    """
    manifest = []
    base_date = datetime(2026, 3, 15, 9, 0, 0)

    # 1. Generate Internal Ledger
    internal_records = []
    internal_count = int(100000 * scale_factor)

    for i in range(1, internal_count + 1):
        merch_id, merch_name, ifsc, acct = random.choice(MERCHANTS)
        txn_id = f"PB260315{i:08d}"
        bank_ref = f"UTR260315{i:08d}"
        amt = Decimal(str(random.choice([150, 499, 999, 1499, 2500, 4800, 12500, 25000, 50000, 120000]))) + Decimal(str(round(random.random(), 2)))
        direction = "CR" if random.random() > 0.15 else "DR"
        offset_mins = random.randint(0, 720)
        txn_dt = base_date + timedelta(minutes=offset_mins)

        rec = {
            "transaction_id": txn_id,
            "bank_ref_no": bank_ref,
            "merchant_name": merch_name,
            "account_number": acct,
            "net_amount": str(amt),
            "currency": "INR",
            "cr_dr": direction,
            "transaction_date": txn_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "settlement_date": (txn_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
            "remarks": f"UPI Payment via PayBridge ID {txn_id}"
        }
        internal_records.append(rec)

    internal_csv_path = os.path.join(DATA_DIR, "internal_ledger_20260315.csv")
    with open(internal_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(internal_records[0].keys()))
        writer.writeheader()
        writer.writerows(internal_records)

    # 2. Generate HDFC CSV (Standard)
    hdfc_count = int(25000 * scale_factor)
    hdfc_records = []
    for i in range(hdfc_count):
        source = internal_records[i]
        rec = dict(source)
        # Plant deliberate exception every ~30 records
        if i % 30 == 0:
            rec["net_amount"] = str(Decimal(rec["net_amount"]) + Decimal("15.50"))
            manifest.append({
                "source_file": "hdfc_settlement_20260315.csv",
                "line": i + 2,
                "txn_id": rec["transaction_id"],
                "category": "AMOUNT_MISMATCH",
                "expected_resolution": "Review bank charge difference"
            })
        elif i % 55 == 0:
            rec["cr_dr"] = "DR" if rec["cr_dr"] == "CR" else "CR"
            manifest.append({
                "source_file": "hdfc_settlement_20260315.csv",
                "line": i + 2,
                "txn_id": rec["transaction_id"],
                "category": "DIRECTION_REVERSAL",
                "expected_resolution": "Escalate to Compliance (30m SLA)"
            })
        hdfc_records.append(rec)

    hdfc_csv_path = os.path.join(DATA_DIR, "hdfc_settlement_20260315.csv")
    with open(hdfc_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(hdfc_records[0].keys()))
        writer.writeheader()
        writer.writerows(hdfc_records)

    # 3. Generate ICICI CSV (Variant column order & headers)
    icici_count = int(18000 * scale_factor)
    icici_records = []
    start_idx = hdfc_count
    for i in range(icici_count):
        idx = (start_idx + i) % len(internal_records)
        source = internal_records[idx]
        rec = {
            "urn_ref": source["transaction_id"],
            "posting_date": source["settlement_date"],
            "payee_name": source["merchant_name"],
            "payee_account": source["account_number"],
            "settlement_value": source["net_amount"],
            "txn_currency": source["currency"],
            "value_date": source["transaction_date"],
            "icici_ref_number": source["bank_ref_no"],
            "txn_indicator": source["cr_dr"],
            "description": f"ICICI EAZYPAY SETTLE {source['bank_ref_no']}"
        }
        if i % 40 == 0:
            rec["urn_ref"] = rec["urn_ref"][:14]  # Truncated reference
            manifest.append({
                "source_file": "icici_settlement_20260315.csv",
                "line": i + 2,
                "txn_id": rec["urn_ref"],
                "category": "REFERENCE_TRUNCATED",
                "expected_resolution": "Prefix auto-rematch"
            })
        icici_records.append(rec)

    icici_csv_path = os.path.join(DATA_DIR, "icici_settlement_20260315.csv")
    with open(icici_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(icici_records[0].keys()))
        writer.writeheader()
        writer.writerows(icici_records)

    # 4. Generate Axis MT940 (.sta) with period decimal separator
    axis_count = int(12000 * scale_factor)
    axis_lines = [
        ":20:AXIS20260315001",
        ":25:910020030040050",
        ":28C:00142/001",
        ":60F:C260315INR50000000.00"
    ]
    start_idx = hdfc_count + icici_count
    for i in range(axis_count):
        idx = (start_idx + i) % len(internal_records)
        source = internal_records[idx]
        amt_str = str(source["net_amount"]).replace(",", ".")
        d_c = "C" if source["cr_dr"] == "CR" else "D"
        # Tag 61: 6-digit date YYMMDD + D/C + amount + NTRF + ref
        axis_lines.append(f":61:260315{d_c}{amt_str}NTRF{source['transaction_id']}//{source['bank_ref_no']}")
        axis_lines.append(f":86:/NAME/{source['merchant_name']}/ACC/{source['account_number']}/REMK/{source['remarks']}")

    axis_lines.append(":62F:C260315INR75000000.00")
    axis_path = os.path.join(DATA_DIR, "axis_mt940_20260315.sta")
    with open(axis_path, "w", encoding="utf-8") as f:
        f.write("\n".join(axis_lines))

    # 5. Generate SBI MT940 (.sta) with missing funds code
    sbi_count = int(20000 * scale_factor)
    sbi_lines = [
        ":20:SBI20260315BATCH",
        ":25:400200100200",
        ":28C:00088/001",
        ":60F:C260315INR100000000,00"
    ]
    start_idx = hdfc_count + icici_count + axis_count
    for i in range(sbi_count):
        idx = (start_idx + i) % len(internal_records)
        source = internal_records[idx]
        amt_str = str(source["net_amount"]).replace(".", ",")
        d_c = "C" if source["cr_dr"] == "CR" else "D"
        # SBI missing funds code: directly amount after D/C without 'N'
        sbi_lines.append(f":61:260315{d_c}{amt_str}STRF{source['transaction_id']}")
        sbi_lines.append(f":86:SBI CBS SETTLEMENT REF {source['bank_ref_no']} {source['merchant_name']}")

    sbi_lines.append(":62F:C260315INR145000000,00")
    sbi_path = os.path.join(DATA_DIR, "sbi_mt940_20260315.sta")
    with open(sbi_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sbi_lines))

    # 6. Generate Kotak CAMT.053 XML
    kotak_count = int(15000 * scale_factor)
    xml_entries = []
    start_idx = (hdfc_count + icici_count + axis_count + sbi_count) % len(internal_records)

    for i in range(kotak_count):
        idx = (start_idx + i) % len(internal_records)
        source = internal_records[idx]
        cdt_dbt = "CRDT" if source["cr_dr"] == "CR" else "DBIT"
        xml_entries.append(f"""
        <Ntry>
            <Amt Ccy="INR">{source['net_amount']}</Amt>
            <CdtDbtInd>{cdt_dbt}</CdtDbtInd>
            <BookgDt><Dt>2026-03-15</Dt></BookgDt>
            <NtryDtls>
                <TxDtls>
                    <Refs>
                        <EndToEndId>{source['transaction_id']}</EndToEndId>
                        <TxId>{source['bank_ref_no']}</TxId>
                    </Refs>
                    <RltdPties>
                        <Cdtr><Nm>{source['merchant_name']}</Nm></Cdtr>
                        <CdtrAcct><Id><IBAN>{source['account_number']}</IBAN></Id></CdtrAcct>
                    </RltdPties>
                    <RmtInf><Ustrd>{source['remarks']}</Ustrd></RmtInf>
                </TxDtls>
            </NtryDtls>
        </Ntry>""")

    kotak_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
    <BkToCstmrStmt>
        <GrpHdr>
            <MsgId>KOTAK-CAMT-20260315-001</MsgId>
            <CreDtTm>2026-03-15T18:00:00Z</CreDtTm>
        </GrpHdr>
        <Stmt>
            <Id>KMB-STMT-20260315</Id>
            <Acct><Id><IBAN>KKBK0002222987654321</IBAN></Id></Acct>
            <Bal>
                <Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
                <Amt Ccy="INR">25000000.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <Dt><Dt>2026-03-15</Dt></Dt>
            </Bal>
            {"".join(xml_entries)}
            <Bal>
                <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
                <Amt Ccy="INR">62500000.00</Amt>
                <CdtDbtInd>CRDT</CdtDbtInd>
                <Dt><Dt>2026-03-15</Dt></Dt>
            </Bal>
        </Stmt>
    </BkToCstmrStmt>
</Document>"""

    kotak_path = os.path.join(DATA_DIR, "kotak_camt053_20260315.xml")
    with open(kotak_path, "w", encoding="utf-8") as f:
        f.write(kotak_xml)

    # 7. Generate FX Rates CSV
    fx_rates_data = [
        {"date": "2026-03-15", "currency": "USD", "rbi_ref_rate": "83.2500", "fbil_rate": "83.2480"},
        {"date": "2026-03-15", "currency": "EUR", "rbi_ref_rate": "90.4500", "fbil_rate": "90.4450"},
        {"date": "2026-03-15", "currency": "GBP", "rbi_ref_rate": "105.8000", "fbil_rate": "105.7900"},
        {"date": "2026-03-15", "currency": "SGD", "rbi_ref_rate": "61.5000", "fbil_rate": "61.4900"},
        {"date": "2026-03-15", "currency": "AED", "rbi_ref_rate": "22.6500", "fbil_rate": "22.6480"},
    ]
    fx_path = os.path.join(DATA_DIR, "fx_rates_20260301_20260315.csv")
    with open(fx_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fx_rates_data[0].keys()))
        writer.writeheader()
        writer.writerows(fx_rates_data)

    # 8. Save Sealed Exceptions Manifest
    manifest_path = os.path.join(DATA_DIR, "sealed_exceptions_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_planted_exceptions": len(manifest),
            "exceptions": manifest
        }, f, indent=2)

    return {
        "data_dir": DATA_DIR,
        "internal_records": len(internal_records),
        "hdfc_records": len(hdfc_records),
        "icici_records": len(icici_records),
        "axis_records": axis_count,
        "sbi_records": sbi_count,
        "kotak_records": kotak_count,
        "planted_exceptions": len(manifest)
    }


if __name__ == "__main__":
    summary = generate_all_datasets(scale_factor=0.05)
    print(f"Generated sample datasets successfully: {summary}")
