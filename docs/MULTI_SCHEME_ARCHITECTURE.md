# Multi-Scheme FieldGuard Architecture

**Document ID:** `DOC-ARCH-002`  
**Version:** 2.0.0 (Stage 2)  
**Project:** FieldGuard  

---

## 1. Architectural Vision

FieldGuard Stage 2 transforms numerical claim verification from a single-scheme crop-insurance verifier into an extensible **Multi-Scheme Verification Framework**.

The central insight of FieldGuard is that numerical hallucinations in RAG for government schemes are dominated by **Condition and Context Mismatches**: numbers that are authentic in the underlying policy documents are retrieved and asserted as facts, but applied to the wrong beneficiary category, calculation basis, instalment window, eligibility bracket, or time period.

By abstracting domain-specific rules into modular scheme adapters while retaining a rigorous, deterministic verification core, FieldGuard scales seamlessly across policy domains.

---

## 2. High-Level Architecture

```
                               ┌─────────────────────────┐
                               │ User Question & Claim   │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │   Hybrid IR Pipeline    │
                               │ (Lexical + Dense BM25)  │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ Retrieved Passages &    │
                               │    Linked Rules         │
                               └────────────┬────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               ▼                                                         ▼
┌─────────────────────────────┐                           ┌─────────────────────────────┐
│    Scheme Adapter Layer     │                           │  Numerical & Temporal Layer │
│  - SchemeRegistry           │                           │  - Numeric Normalizer       │
│  - PMFBYScheme              │                           │  - Temporal Resolver        │
│  - PMKisanScheme            │                           │  - Unit & Basis Matcher     │
└──────────────┬──────────────┘                           └──────────────┬──────────────┘
               │                                                         │
               └────────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │   Condition Matcher     │
                               │   (Generic Predicates)  │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ FieldGuard 10-Step Core │
                               │ - Provenance Gate       │
                               │ - Sufficiency Gate      │
                               │ - Context Gate          │
                               │ - Temporal Gate         │
                               │ - Qualification Gate    │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │   Structured Verdict    │
                               │ SUPPORTED / CONTRADICTED│
                               │ WRONG_CONTEXT / UNVERIF │
                               └─────────────────────────┘
```

---

## 3. Scheme Plugin Subsystem (`src/fieldguard/schemes/`)

### 3.1 Registry Pattern
The `SchemeRegistry` serves as the central hub:
- Supports runtime registration of new scheme definitions (`register_scheme`).
- Resolves scheme names case-insensitively and maps common aliases (e.g. `"PM-KISAN"`, `"pmkisan"`, `"kisan_samman_nidhi"` all resolve to `PM_KISAN`).
- Exposes standard scheme introspection capabilities.

### 3.2 Scheme Adapter Contract (`BaseScheme`)
Every scheme plugin implements three mandatory interfaces:
1. `validate_claim_context(rule_parameter, context_dict, enable_switches)`: Determines whether a parsed claim contains all mandatory contextual dimensions needed to verify that parameter (preventing unconstrained guesses).
2. `match_conditions(claimed_context, rule_context, rule_parameter, enable_switches)`: Evaluates whether the claimed conditions (beneficiary, season, category, frequency, etc.) match the evidence rule.
3. `get_required_context_keys(rule_parameter)`: Lists the required condition keys for a specific parameter.

---

## 4. Evaluated Schemes

### 4.1 Pradhan Mantri Fasal Bima Yojana (PMFBY)
- **Domain:** Agriculture / Crop Insurance.
- **Key Parameters:** Farmer premium rates (2% Kharif, 1.5% Rabi, 5% Commercial/Horticultural), central subsidy actuarial caps (30% un-irrigated, 25% irrigated), subsidy sharing ratios (90:10 NER, 50:50 general).
- **Condition Dimensions:** `crop_category`, `season`, `geography`, `mandatory_qualifier` (*"or Actuarial rate, whichever is less"*).

### 4.2 Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)
- **Domain:** Direct Income Support / Agriculture DBT.
- **Key Parameters:**
  - Annual income support: ₹6,000 / year.
  - Instalment value: ₹2,000 / instalment.
  - Number of instalments: 3 per year (4 months per period).
  - Landholding limit: 2 hectares (historical launch era: Feb 2019) -> all landholding farmers (June 2019 onwards).
  - Mandatory compliance: 100% Aadhaar-seeded accounts and mandatory eKYC.
- **Condition Dimensions:**
  - `beneficiary_type`: Landholding farmer family vs. tenant farmer / agricultural laborer.
  - `exclusion_category`: Institutional landholders, constitutional post holders, government employees, pensioners $\ge$ ₹10,000, income tax payees, professionals.
  - `frequency`: Annual vs. per-instalment.
  - `policy_era`: `original_launch_feb2019` vs `universal_landholder_2019_onwards`.

### 4.3 Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA)
- **Domain:** Rural Wage Employment & Livelihood Security.
- **Key Parameters:**
  - Statutory entitlement: **100 days** of guaranteed wage employment per financial year per rural household.
  - Work allocation timeline: **15 days** from application date.
  - Unemployment allowance: Payable if work is not allotted within statutory 15 days.
- **Condition Dimensions:** `beneficiary_type` (rural household with adult members volunteering for unskilled manual labor), `geography` (`rural_areas`).

### 4.4 Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY)
- **Domain:** Health Assurance & Hospitalisation Coverage.
- **Key Parameters:**
  - Annual health cover: **₹5,00,000** per eligible family per year.
  - Cashless treatment: **100% cashless and paperless** secondary/tertiary hospitalisation.
  - Family cap: **No limit** on family size, age, or gender.
- **Condition Dimensions:** `beneficiary_type` (deprived rural and identified occupational urban households per SECC 2011), `treatment_level` (`secondary_tertiary_care`).

### 4.5 Pradhan Mantri Awas Yojana — Gramin (PMAY-G)
- **Domain:** Rural Housing & Infrastructure.
- **Key Parameters:**
  - Plain areas unit assistance: **₹1,20,000** grant.
  - Hilly, difficult, and IAP areas unit assistance: **₹1,30,000** grant.
  - Minimum floor area: **25 sq. metres** (including hygienic cooking area).
  - Toilet assistance: **₹12,000** via Swachh Bharat Mission (SBM-G) convergence.
- **Condition Dimensions:** `geography` (`plains_areas` vs `hilly_areas`), `beneficiary_type` (homeless/kutcha house owners).

### 4.6 PM-KUSUM (Solar Agriculture)
- **Domain:** Renewable Energy & Solar Pumps.
- **Key Parameters:**
  - Total capital subsidy: **60%** (30% Central Financial Assistance CFA + 30% State Govt subsidy).
  - Farmer contribution: **40%** (minimum 10% upfront cash + up to 30% bank credit).
  - Pump capacity ceiling: Standalone solar pumps up to **7.5 HP**.
- **Condition Dimensions:** `scheme_component` (`component_b_standalone_pumps`), `pump_capacity` ($\le 7.5\text{ HP}$).

### 4.7 Pradhan Mantri Mudra Yojana (PMMY)
- **Domain:** Micro-Enterprise & MSME Credit.
- **Key Parameters:**
  - Shishu category: Micro-loans up to **₹50,000**.
  - Kishore category: Loans from **₹50,000 to ₹5,00,000**.
  - Tarun category: Loans from **₹5,00,000 to ₹10,00,000** (expanded to ₹20,00,000 under budget revision).
  - Security: **100% collateral-free**.
- **Condition Dimensions:** `loan_category` (`shishu`, `kishore`, `tarun`).

### 4.8 Dynamic Upload Scheme (`GenericUploadedScheme`)
- **Domain:** Arbitrary National or State Government Policy Documents (PDF / TXT).
- **Engine:** [`uploaded_doc_engine.py`](file:///c:/FieldGuard_ag/src/fieldguard/uploaded_doc_engine.py).
- **Capabilities:**
  - In-memory parsing of text chunks and table rows via `pypdf`.
  - Automated candidate rule induction with page-scoped parameter naming (`rule_p{page}_{unit}_{val}`) preventing false conflicts.
  - Page-grounded Natural Language Q&A with physical citations and condition-aware numerical claim verification.

---

## 5. Adding New Government Schemes

To extend FieldGuard to a new scheme (e.g., Ayushman Bharat PM-JAY, PM Awas Yojana):
1. Create `src/fieldguard/schemes/<scheme_name>.py` subclassing `BaseScheme`.
2. Define the parameter taxonomy and context validation logic.
3. Register the scheme in `SchemeRegistry.initialize_default_schemes()`.
4. Ingest authoritative policy documents and extract structured rules into the `EvidenceStore`.
5. No modifications to `FieldGuardVerifier` or `verifier.py` are required.

