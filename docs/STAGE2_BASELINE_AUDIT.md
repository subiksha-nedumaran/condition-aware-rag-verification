
# Stage 2 Baseline Audit & Multi-Scheme Generalization Roadmap

**Document ID:** `DOC-STAGE2-AUDIT-001`  
**Date:** 2026-10-30  
**Project:** FieldGuard — Multi-Scheme Numerical Claim Verification  
**Status:** Approved Baseline Audit  

---

## 1. Executive Summary

FieldGuard Stage 1 established a condition-aware numerical claim verification pipeline evaluated on India's crop insurance policy: **Pradhan Mantri Fasal Bima Yojana (PMFBY)**. In Stage 1, FieldGuard demonstrated that standard retrieval-augmented generation (RAG) and numeric-matching baselines suffer from acute **False Support Rates (FSR = 86.84% in Baseline A and 55.26% in Baseline B)**, whereas FieldGuard achieves:
- **Accuracy:** 94.05%
- **False Support Rate (FSR):** 2.63%
- **Answer / Decision Coverage:** 82.14%
- **Retrieval Item Recall@5:** 91.15% (Hybrid)

The objective of **Stage 2** is to upgrade FieldGuard into a **generalizable, configurable multi-scheme framework** capable of verifying numerical claims across diverse government policy domains without hard-coding scheme-specific attributes (such as crops or agricultural seasons) into the core verification engine.

The primary independent evaluation scheme selected for Stage 2 is **Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)**, India's flagship direct benefit transfer (DBT) income support scheme for agricultural households.

This document records the complete baseline audit of the existing workspace, details the architectural limitations of Stage 1, and defines the roadmap for Stage 2 migration with a strict **zero-regression guarantee** on PMFBY.

---

## 2. Workspace & Codebase Audit

### 2.1 Directory Structure
The workspace at `C:\FieldGuard_ag` contains:
```
FieldGuard_ag/
├── app.py                      # Interactive Streamlit Web UI (running on localhost:8501)
├── pyproject.toml              # Project configuration and dependency specifications
├── README.md                   # Project overview and reproduction instructions
├── src/fieldguard/             # Core Python package
│   ├── benchmark_builder.py    # PMFBY benchmark construction & cluster stratification
│   ├── chunking.py             # Section-aware document chunker
│   ├── claim_parser.py         # Deterministic rule-based claim parser
│   ├── claim_parser_llm.py     # Optional LLM-assisted claim parser
│   ├── cli.py                  # Unified command-line interface
│   ├── condition_matcher.py    # Semantic condition, basis, and qualifier matcher
│   ├── data_acquisition.py     # Source document ingestion & integrity checks
│   ├── document_extraction.py  # Text and layout extraction
│   ├── evidence_schema.py      # Structured rule schema & validation
│   ├── evidence_store.py       # Evidence store with provenance & conflict detection
│   ├── metadata.py             # Evidence unit and provenance metadata schemas
│   ├── numeric_normalizer.py   # Tokenization, units, currency, and numerical comparison
│   ├── source_manifest.py      # Source document manifest and cryptographic checksums
│   ├── table_extraction.py     # Precision table extraction & cell linking
│   ├── temporal_resolver.py    # Temporal validity & policy version resolution
│   ├── verdicts.py             # Verdict enumeration (SUPPORTED, CONTRADICTED, WRONG_CONTEXT, UNVERIFIABLE)
│   ├── verifier.py             # 10-step verification decision pipeline
│   ├── evaluation/             # Evaluation harness, metrics, bootstrap CI, error analysis
│   └── retrieval/              # Lexical, semantic, hybrid, and table-aware retrievers
├── tests/                      # Automated test suite (51 unit, integration, and regression tests)
├── data/                       # Raw documents, manifests, processed chunks, and benchmark splits
└── docs/                       # Research documentation, methodology, limitations, and reports
```

### 2.2 Baseline Test Suite Status
Prior to initiating Stage 2 development, the complete automated test suite was executed in the workspace virtual environment:
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```
**Results:**
- **Passed:** 51 / 51 tests (100%)
- **Duration:** 3.83 seconds
- **Failures / Errors:** 0
- **Regression Invariants:** All existing PMFBY regression tests (`tests/test_regression.py`, `tests/test_verifier.py`, `tests/test_condition_matcher.py`, `tests/test_temporal_resolver.py`, `tests/test_cli.py`) are passing.

---

## 3. Detailed Architectural Limitations of Stage 1

While FieldGuard Stage 1 successfully solved condition-aware verification for PMFBY, several components contain **domain-specific hardcoding** that inhibits seamless multi-scheme scaling:

### 3.1 Hardcoded Evidence Schema (`evidence_schema.py`)
In Stage 1, `StructuredRuleRecord` has domain-specific fields explicitly declared:
```python
@dataclass
class StructuredRuleRecord:
    rule_id: str
    evidence_id: str
    scheme: str
    rule_parameter: str
    season: str | None          # PMFBY-specific (Kharif, Rabi, Annual)
    crop_category: str | None   # PMFBY-specific (Food grain, Horticultural, etc.)
    geography: str | None
    ...
```
**Limitation:** A non-insurance scheme like PM-KISAN does not operate on crops or seasons. PM-KISAN operates on:
- Beneficiary eligibility (landholding farmer families vs. tenant farmers vs. institutional landholders).
- Benefit periodicity and instalments (₹6,000 per year, ₹2,000 per 4-month instalment).
- Statutory exclusion criteria (income tax payees, constitutional post holders, institutional owners, pensions $\ge$ ₹10,000).
- Operational verification mandates (eKYC, Aadhaar-seeded bank accounts, land registry records).

### 3.2 Hardcoded Condition Matcher (`condition_matcher.py`)
In Stage 1, `condition_matcher.py` relies on dedicated functions:
- `_match_season(...)`
- `_match_crop_category(...)`
- `_match_geography(...)`
- Specific PMFBY rules like `annual` season matching commercial/horticultural crops across Kharif and Rabi.

**Limitation:** These functions cannot evaluate PM-KISAN conditions such as `exclusion_criterion`, `landholding_cutoff_date`, or `instalment_period` without generic predicate matching.

### 3.3 Hardcoded Verifier Preconditions (`verifier.py`)
In `FieldGuardVerifier._run_fieldguard_pipeline`, lines 378–393 explicitly enforce PMFBY contextual requirements:
```python
if parsed.rule_parameter == "farmer_premium_rate":
    if self.config.enable_crop_category_matching and parsed.crop_category is None:
        missing_context.append("crop_category")
    if (
        self.config.enable_season_matching
        and parsed.season is None
        and parsed.crop_category != "commercial_and_horticultural"
    ):
        missing_context.append("season")
```
**Limitation:** If a claim asserts `rule_parameter="annual_benefit_amount"` or `rule_parameter="instalment_amount"`, the verifier must check scheme-appropriate contextual parameters (e.g., beneficiary group, exclusion status, fiscal period) rather than hard-coding PMFBY parameter names.

### 3.4 Hardcoded Conflict Detection (`evidence_store.py`)
In `EvidenceStore._detect_and_flag_conflicts`, rules are grouped by a hard-coded 6-tuple:
```python
key = (r.scheme, r.rule_parameter, r.season, r.crop_category, r.geography, r.policy_era)
```
**Limitation:** For generic schemes, conflict grouping must operate on `(scheme, rule_parameter, normalized_context_hash, policy_era)`.

---

## 4. Stage 2 Multi-Scheme Architectural Strategy

To achieve clean multi-scheme support while preserving 100% backward compatibility with PMFBY, FieldGuard Stage 2 adopts a **modular Scheme Adapter and Generic Predicate Architecture**:

```
                       ┌─────────────────────────┐
                       │  ParsedClaim / Query    │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   Scheme Registry &     │
                       │   Domain Adapter        │
                       │ (PMFBY / PM-KISAN / Base)│
                       └────────────┬────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
┌───────────────────────────┐                   ┌───────────────────────────┐
│ Generic Condition Vector  │                   │ Generic Evidence Schema   │
│ - scheme                  │                   │ - rule_id                 │
│ - rule_parameter          │                   │ - scheme                  │
│ - primary_value & unit    │                   │ - rule_parameter          │
│ - entity_scope            │                   │ - numeric constraint      │
│ - temporal_scope          │                   │ - entity_scope            │
│ - eligibility_conditions  │                   │ - conditions & exclusions │
│ - exclusions              │                   │ - temporal validity       │
│ - calculation_basis       │                   │ - mandatory qualifiers    │
│ - qualifiers              │                   │ - exact provenance        │
└───────────┬───────────────┘                   └───────────┬───────────────┘
            │                                               │
            └───────────────────────┬───────────────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │ Generalized Condition   │
                       │      Matcher            │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ FieldGuard Core Engine  │
                       │ (10-Step Decision Logic)│
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │  Traceable Verdict &    │
                       │       Rationale         │
                       └─────────────────────────┘
```

### 4.1 Schema Generalization
1. Introduce `GenericEvidenceRecord` in `src/fieldguard/evidence_schema.py` supporting:
   - `entity_scope`: Beneficiary category, target population, or crop/commodity.
   - `conditions`: Key-value or predicate constraints (e.g. `season="kharif"`, `landholding="cultivable"`, `ekyc="completed"`).
   - `exclusions`: Specific disqualifying attributes (e.g. `institutional_landholder`, `income_tax_payee`).
   - `frequency` / `periodicity`: `annual`, `four_monthly_instalment`, `one_time`.
   - `calculation_basis`: `sum_insured`, `direct_cash_transfer`, `fixed_statutory`.
   - Full provenance: `source_document_id`, `physical_pdf_page`, `table_id`, `row_id`, `verification_status`.
2. Provide a bidirectional adapter between `StructuredRuleRecord` and `GenericEvidenceRecord` so that all existing 51 PMFBY tests continue to pass without alteration.

### 4.2 Modular Scheme Registry (`src/fieldguard/schemes/`)
Create a scheme plugin architecture:
- `base.py`: Abstract `BaseSchemeDefinition` defining schema mappings, alias resolution, required contextual dimensions, and validation rules.
- `pmfby.py`: PMFBY scheme adapter mapping `crop_category` and `season` into the generic condition structure.
- `pm_kisan.py`: PM-KISAN scheme adapter mapping `beneficiary_type`, `instalment_number`, `exclusion_type`, and `landholding_size`.

### 4.3 PM-KISAN Corpus Ingestion
Ingest official, authoritative government documents for PM-KISAN:
1. **Operational Guidelines of PM-KISAN (Revised 2019/2020)** from the Ministry of Agriculture & Farmers Welfare (MoA&FW).
2. **Official Scheme FAQs & eKYC / Aadhaar Mandates** from `pmkisan.gov.in`.
3. **Press Information Bureau (PIB) Cabinet Notifications** regarding scheme coverage expansion (cabinet decision of June 2019 removing the 2-hectare ceiling).
4. Extract text passages, structural tables, and create cryptographically hashed manifest entries in `data/manifests/pm_kisan_manifest.json`.

### 4.4 Cluster-Stratified Benchmark Construction
Construct a rigorous, leakage-free evaluation benchmark for PM-KISAN:
- Balanced distribution across verdicts: `SUPPORTED`, `CONTRADICTED`, `WRONG_CONTEXT`, `UNVERIFIABLE`.
- Sub-clusters covering:
  - Total annual benefit (₹6,000/year).
  - Instalment value and schedule (₹2,000/instalment across three periods: Apr–Jul, Aug–Nov, Dec–Mar).
  - Historical policy shift (Initial 2 ha land ceiling in Feb 2019 vs. universal landholder coverage in June 2019).
  - Statutory exclusion criteria (Institutional holders, constitutional post holders, income tax payees, monthly pension $\ge$ ₹10,000).
  - Mandatory compliance requirements (Aadhaar seeding, mandatory eKYC).
  - Wrong-context distractors (e.g., claiming ₹6,000 per instalment, or applying PM-KISAN benefits to tenant farmers without land ownership).
- Strict separation into **Development Set** and **Frozen Test Set** stratified by claim family to prevent test contamination.

---

## 5. Execution Milestones & Deliverables

| Milestone | Deliverable | Description |
|---|---|---|
| **Phase 1** | `docs/STAGE2_BASELINE_AUDIT.md` | Workspace & architectural audit (this document) |
| **Phase 2** | `src/fieldguard/evidence_schema.py`, `src/fieldguard/schemes/` | Generalized evidence data model & scheme adapters |
| **Phase 3** | `data/raw/documents/pm_kisan/`, `data/manifests/` | PM-KISAN corpus ingestion, manifest, and table extraction |
| **Phase 4** | `src/fieldguard/condition_matcher.py`, `verifier.py` | Generalized condition matcher and verifier core |
| **Phase 5** | `data/benchmark/pm_kisan/` | PM-KISAN benchmark dataset with cluster-stratified test freeze |
| **Phase 6** | `tests/test_stage2_*.py` | Multi-scheme unit & regression tests (verifying PMFBY 0 regressions) |
| **Phase 7** | Multi-Scheme Experiments | Evaluation of Baselines A, B, C, D & ablations on PM-KISAN |
| **Phase 8** | Cross-Scheme Transfer Analysis | Zero-shot evaluation of PMFBY-tuned rules on PM-KISAN |
| **Phase 9** | `docs/STAGE2_RESULTS.md`, `docs/STAGE2_COMPLETION_REPORT.md` | Comprehensive research results, error analysis, and thesis artifacts |

---

## 6. Zero-Regression Assurance

At each step of the Stage 2 implementation, the complete existing test suite (`pytest tests/`) will be executed. Any code change that alters the predictions, accuracy, false support rate, or coverage of PMFBY Stage 1 is treated as a blocking defect.
