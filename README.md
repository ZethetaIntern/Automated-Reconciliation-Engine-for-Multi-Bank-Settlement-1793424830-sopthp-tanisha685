# Automated Reconciliation Engine for Multi-Bank Settlement
### PayBridge Settlement Guardian (ReconOps v1.0)

> **STRICTLY CONFIDENTIAL – FOR ASSESSMENT & INTERNAL EVALUATION ONLY**  
> *Property of Zetheta Algorithms Private Limited ("Zetheta").*  
> Developed for: Undergraduate / MBA / CA (Inter) Technical Assessment.

---

## 1. System Summary

The **Automated Reconciliation Engine for Multi-Bank Settlement** is an enterprise financial infrastructure solution designed for payment aggregators and FinTech platforms processing high-velocity transaction volumes across multiple banking partners.

### Core Capabilities:
- **Multi-Format Ingestion**: Streaming parsers for **SWIFT MT940**, **ISO 20022 CAMT.053 (XML)**, and **bank-specific CSV layouts** (HDFC, ICICI, Axis, SBI, Kotak, Yes Bank, IndusInd).
- **Canonical Normalisation**: 10-field single source of truth, UTC timezone conversion, fixed-point **Decimal banker's rounding (`ROUND_HALF_EVEN`)**, and **PCI DSS PAN masking**.
- **Three-Tier Matching Engine**:
  1. *Exact Matching (O(N+M))*: Hash composite index with disambiguation.
  2. *Candidate-Blocked Fuzzy Matching*: RapidFuzz Jaro-Winkler (>0.92), Levenshtein (dist <= 2), and Token Set Ratio (>0.80).
  3. *Rule-Based & Subset-Sum Solvers*: Dynamic programming for 1-to-N split transactions, N-to-1 netted settlements, and cross-currency FX tolerance bands (1.5%).
- **18-Category Exception Triage & Escalation**: Tiered SLA enforcement (e.g. `DIRECTION_REVERSAL` 30m SLA to Compliance) and Tier 1 auto-resolutions.
- **Cryptographic Audit Trail**: Immutable append-only ledger with **SHA-256 block hash chaining** satisfying Section 128 of the Companies Act, 2013.
- **ReconOps Gamified Simulation Hub**: 7 Campaign Levels, 20 Badges across 5 tiers, and 6 Real-World Case Study Scenarios (Paytm, Citibank Revlon, NPCI Rounding, Wirecard, Yes Bank, Target).
- **Statutory Reporting**: Daily Reconciliation Report, Exception Ageing Matrix, and RBI Clause 7.1 Escrow Compliance.

---

## 2. Quick Start

### A. Run Backend & Frontend in Local Environment
```bash
# 1. Start FastAPI Backend (serves pre-built dashboard directly)
py -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to access the institutional operations dashboard.

### B. Run Database Seeder & Test Suite
```bash
# 1. Execute end-to-end database seeder (initializes DB, multi-bank run, balance check)
py seed_data.py

# 2. Run complete automated test suite (25 tests covering all parsers, matching, exceptions, reports)
py -m pytest backend/tests -v
```

### C. Docker Deployment
```bash
# Production Compose:
docker compose up --build -d

# CI/CD Automated Test Runner Compose:
docker compose -f docker-compose.test.yml up --build
```

---

## 3. Deliberate Errors Detected & Corrected

| # | Spec Inaccuracy | Root Cause Analysis | Code Correction |
|---|---|---|---|
| **1** | MT940 `:86:` at line 2–3 & CAMT.053 `CLBD` only | Tag `:86:` has no fixed line numbering. CAMT.053 distinguishes Closing Booked (`CLBD`) from Closing Available (`CLAV`). | Multi-tag regex & explicit `CLBD`/`CLAV` balance extraction in parsers. |
| **2** | `DIRECTION_REVERSAL` SLA listed as 1 hour | DR/CR reversal indicates critical booking failure or fraud risk requiring immediate executive intervention. | Corrected to **30 minutes critical SLA** with direct escalation to **Tier 4 (Compliance & Risk)**. |
| **3** | NPCI rounding attributed to Round Half Up | NPCI settlement strictly mandates Banker's Rounding (`ROUND_HALF_EVEN`); drift was caused by member bank float math. | Implemented `decimal.Decimal(ROUND_HALF_EVEN)` throughout the entire arithmetic pipeline. |
| **4** | Target breach timeline conflation | Breach involved distinct infection (Nov 15), exfiltration (Nov 27–Dec 15), and disclosure dates (Dec 19, 2013). | Reflected correct chronological milestones in case study scenarios and enforced PAN masking. |

---

## 4. Repository Structure

```
project1b/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI Application & Lifecycle
│   │   ├── models/                  # Canonical Model, Schemas, DB Models & Persistence
│   │   ├── parsers/                 # CSV, MT940 State Machine, CAMT.053 XML
│   │   ├── normalisation/           # Timezone UTC, Decimal Math, PAN Masking
│   │   ├── matching/                # Exact Hash, RapidFuzz Fuzzy, Subset-Sum Rules
│   │   ├── exceptions/              # 18-Category Classifier, Escalation, Auto-Resolver
│   │   ├── audit/                   # SHA-256 Hash Chaining & Tamper Verifier
│   │   ├── anomaly/                 # Whale Alert, Velocity, Feed Absence
│   │   ├── reconops/                # Game Engine, 20 Badges, 6 Case Study Scenarios
│   │   ├── reports/                 # Daily HTML/CSV, Ageing CSV, RBI Escrow 7.1
│   │   └── api/                     # REST API Routers (Recon, Exceptions, Audit, Reports, Files, ReconOps)
│   ├── config/                      # 7 Bank YAML Mapping Schemas (HDFC, ICICI, Axis, SBI, Kotak, Yes, IndusInd)
│   ├── data/                        # Synthetic Multi-Bank Data Generator & Manifest
│   └── tests/                       # 25 Unit & Integration Tests (100% Pass)
├── frontend/                        # Institutional React Operations Workbench (Vite / React 18)
├── docs/                            # ARCHITECTURE.md, API.md, DEPLOYMENT.md, DELIBERATE_ERRORS_ANALYSIS.md
├── seed_data.py                     # Multi-Bank Pipeline Seeder & Verification
├── Dockerfile                       # Multi-Stage Production Container
├── docker-compose.yml               # Service Orchestration
├── docker-compose.test.yml          # Automated CI/CD Testing Compose
├── .env.example                     # Environment Configuration Template
├── LICENSE                          # Proprietary - Zetheta Algorithms Private Limited
└── README.md                        # Documentation & Attribution
```
