# PayBridge Reconciliation Engine: REST API Documentation

Base URL: `http://localhost:8000` (or `/api/v1`)

---

## 1. Reconciliation Operations

### `POST /api/v1/reconciliation/run`
Triggers an automated multi-bank reconciliation run.
- **Request Body**:
  ```json
  {
    "bank_code": "ALL",
    "fast_mode": false,
    "tolerance_amount": 0.01,
    "tolerance_fx": 0.015,
    "date_offset_days": 1
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "status": "SUCCESS",
    "run_id": "RUN-20260330101500-A98B",
    "summary": {
      "match_rate": 98.6,
      "exact_matches": 82500,
      "fuzzy_matches": 10200,
      "rule_matches": 5700,
      "duration_ms": 385.4
    },
    "anomalies_count": 1
  }
  ```

### `GET /api/v1/reconciliation/runs`
Lists all reconciliation runs with status, durations, and balance validation.

### `GET /api/v1/reconciliation/runs/{run_id}/results`
Returns paginated match results with confidence breakdown scores.

---

## 2. Exception Management

### `GET /api/v1/exceptions`
Query parameters: `status`, `category`, `severity`, `bank_code`, `limit`, `offset`.

### `PUT /api/v1/exceptions/{exception_id}/resolve`
- **Request Body**:
  ```json
  {
    "resolution_action": "MANUAL_MATCH",
    "resolution_notes": "Verified with HDFC statement credit advice UTR-88129",
    "resolved_by": "ops_analyst_1"
  }
  ```

---

## 3. Cryptographic Audit Trail

### `GET /api/v1/audit`
Returns chained audit entries with `prev_hash` and `sha256_hash`.

### `GET /api/v1/audit/verify`
Walks and recalculates entire SHA-256 chain to detect any tampering.

---

## 4. Dashboard & Compliance Reports

- `GET /api/v1/dashboard/summary`: Aggregate KPIs, match rates, category counts, daily 7-day trend.
- `GET /api/v1/dashboard/banks`: Bank-wise performance breakdown, match rates, exceptions, and SLA compliance.
- `GET /api/v1/dashboard/timeline`: Hourly transaction processing volume and match rates.
- `GET /api/v1/dashboard/anomalies`: Anomaly alerts (Whale transaction, Velocity spike, Feed absence).
- `GET /api/v1/reports/daily`: Daily reconciliation summary JSON.
- `GET /api/v1/reports/daily/html`: Institutional printable HTML Daily Reconciliation Report.
- `GET /api/v1/reports/daily/csv`: Excel-compatible CSV export of daily bank settlements.
- `GET /api/v1/reports/ageing`: Exception ageing matrix (<1h, 1-4h, 4-24h, >24h) JSON.
- `GET /api/v1/reports/ageing/csv`: Excel-compatible CSV export of exception ageing.
- `GET /api/v1/reports/escrow`: RBI Clause 7.1 Escrow balance verification JSON.
- `GET /api/v1/reports/escrow/html`: Formal statutory RBI Clause 7.1 Escrow certificate HTML.
- `GET /api/v1/reports/audit-compliance`: Statutory audit certificate with SHA-256 chain verification.

---

## 5. File Ingestion & Parsing

### `POST /api/v1/files/upload`
Uploads and parses a bank statement file with auto-detection of format.
- **Form Data**: `file` (multipart), `bank_code` (e.g., `HDFC`, `ICICI`, `AXIS`, `SBI`, `KOTAK`).
- **Response**: `200 OK`
  ```json
  {
    "status": "SUCCESS",
    "filename": "hdfc_settlement.csv",
    "bank_code": "HDFC",
    "detected_format": "CSV",
    "records_ingested": 1250,
    "parse_errors_count": 0,
    "file_hash_sha256": "3a8b41..."
  }
  ```

### `GET /api/v1/files`
Lists all ingested files with timestamps, record counts, and SHA-256 integrity hashes.

---

## 6. ReconOps Gamified Simulation Hub

- `GET /api/v1/reconops/state`: Retrieves player XP, current campaign level (1-7), unlocked badges (20 total), and active scenario.
- `POST /api/v1/reconops/action`: Awards XP for operations actions (parsing, matching, SLA resolution).
- `POST /api/v1/reconops/scenario/run`: Triggers one of 6 real-world crisis scenarios (Paytm Avalanche, Citibank Whale, NPCI Penny Drift, Wirecard Phantom, Yes Bank Frozen, Target Silent Leak).
