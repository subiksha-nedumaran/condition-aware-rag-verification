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

---

## 5. Adding New Government Schemes

To extend FieldGuard to a new scheme (e.g., Ayushman Bharat PM-JAY, PM Awas Yojana):
1. Create `src/fieldguard/schemes/<scheme_name>.py` subclassing `BaseScheme`.
2. Define the parameter taxonomy and context validation logic.
3. Register the scheme in `SchemeRegistry.initialize_default_schemes()`.
4. Ingest authoritative policy documents and extract structured rules into the `EvidenceStore`.
5. No modifications to `FieldGuardVerifier` or `verifier.py` are required.

