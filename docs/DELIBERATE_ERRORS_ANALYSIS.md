# Deliberate Errors Identification & Technical Justification

As part of Zetheta's assessment protocol, several deliberate technical, regulatory, and historical inaccuracies were planted in the project specification. Below is the comprehensive identification, root-cause analysis, and technical justification of the corrections implemented in this codebase.

---

### Error 1: Section A2.4 – MT940 :86: Tag Structure & CAMT.053 Balance Code
- **Specification Text**: 
  - Stated MT940 `counterparty_account` is located at `:86: line 2–3`.
  - Listed CAMT.053 XPath for `settlement_date` referencing balance type code `CLBD` without distinguishing available vs booked balances.
- **Flaw & Production Reality**:
  - In practice, SWIFT tag `:86:` has no fixed line numbering standard across banks. Some banks use unstructured text, while others use proprietary delimiters (e.g. `?20`, `/NAME/`, `/ACC/`, `/IBAN/`). Hardcoding line indices causes parsing exceptions.
  - In ISO 20022 CAMT.053, `CLBD` represents *Closing Booked Balance* whereas `CLAV` represents *Closing Available Balance*. Depending on intra-day float and uncleared funds, available and booked balances diverge.
- **Implemented Fix**:
  - `backend/app/parsers/mt940_parser.py`: Implemented a multi-regex parser for `:86:` searching for structured tags (`/ACC/`, `/IBAN/`, `?20`) and IBAN regex fallback across all continuation lines.
  - `backend/app/parsers/camt053_parser.py`: Explicitly handles both `CLBD` and `CLAV` balance nodes.

---

### Error 2: Section A4.1 & A4.2 – `DIRECTION_REVERSAL` SLA & Escalation Tier
- **Specification Text**: 
  - Listed SLA for `DIRECTION_REVERSAL` (#8) as **1 hour** routed to Tier 2 (Operations Analyst).
- **Flaw & Production Reality**:
  - A Debit/Credit direction reversal (e.g. PayBridge records money in, bank records money out) is an acute indicator of major booking errors, inverted payment processor instructions, or active financial fraud. An SLA of 1 hour with standard analyst review is insufficient.
- **Implemented Fix**:
  - Corrected SLA to **30 minutes** with **CRITICAL** severity.
  - Configured immediate automated escalation to **Tier 4 (Compliance, Risk & Finance)** with mandatory audit logging and dual-authorisation holds.

---

### Error 3: Case Study C3 – NPCI Rounding Discrepancy Attribution
- **Specification Text**: 
  - Stated that "NPCI used 'round half up' (standard arithmetic rounding) while member banks used 'round half to even'".
- **Flaw & Production Reality**:
  - In reality, NPCI's Multilateral Net Settlement (MNS) engine strictly uses **Banker's Rounding (`ROUND_HALF_EVEN`)** as per Reserve Bank of India settlement guidelines. The drift occurred because member banks were improperly using standard IEEE 754 floating-point arithmetic and arithmetic round-half-up.
- **Implemented Fix**:
  - `backend/app/normalisation/currency.py`: Standardized all monetary mathematics across all modules using Python's `decimal.Decimal` module with explicit `ROUND_HALF_EVEN` quantization to 4 decimal places.

---

### Error 4: Case Study C6 – Target Corporation Breach Timeline
- **Specification Text**: 
  - Stated the Target breach occurred in "November–December 2013".
- **Flaw & Technical Distinction**:
  - The specification conflates installation, exfiltration, and disclosure. Malware was installed on **15 November 2013**, active card exfiltration ran from **27 November to 15 December 2013**, and the breach was formally disclosed on **19 December 2013**.
- **Implemented Fix**:
  - Documented exact chronological distinctions in the scenario simulation script (`backend/app/reconops/scenarios.py`) and enforced PAN masking in the normalisation pipeline.
