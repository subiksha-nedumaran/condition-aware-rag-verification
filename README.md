# FieldGuard: Condition-Aware Verification of Numerical Claims in Government-Scheme Question Answering Using RAG

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 84 Passed](https://img.shields.io/badge/tests-84%20passed-brightgreen.svg)](tests/)
[![Accuracy: 94.05%](https://img.shields.io/badge/PMFBY%20Accuracy-94.05%25-green.svg)](results/metrics/)
[![PM-KISAN Accuracy: 92.31%](https://img.shields.io/badge/PM--KISAN%20Accuracy-92.31%25-green.svg)](docs/STAGE2_RESULTS.md)
[![False Support Rate: 2.63%](https://img.shields.io/badge/FSR-2.63%25-brightgreen.svg)](results/metrics/)
[![Schemes: 7 Flagship + Upload](https://img.shields.io/badge/schemes-7%20Flagship%20%2B%20Custom%20Upload-blueviolet.svg)](src/fieldguard/schemes/)
[![License: MIT](https://img.shields.io/badge/license-MIT-informational.svg)](LICENSE)

**FieldGuard** is a research-oriented MSc Data Science capstone project developing and empirically evaluating a condition-aware numerical claim verification pipeline for Retrieval-Augmented Generation (RAG) in public policy question answering.

The framework supports **7 major flagship Indian welfare schemes** alongside a **Dynamic Document Ingestion Engine** that parses arbitrary government policy documents (`.pdf` / `.txt`) for instant Question Answering with page citations and condition-aware numerical claim verification.

---

## 1. Supported Schemes & Dynamic Capabilities

| Mode / Scheme | Domain | Core Policy Rules | Key Invariants Verified |
| :--- | :--- | :--- | :--- |
| 🌾 **PMFBY** | Crop Insurance | 2% Kharif food grains, 1.5% Rabi food grains, 5% commercial/horticultural crops; 100% State wild animal add-on. | *"Whichever is less"* qualifier, crop categories, seasons, gazette amendment resolution. |
| 🚜 **PM-KISAN** | Direct Income Support | ₹6,000/yr in 3 four-monthly instalments of ₹2,000; statutory exclusions (institutional landholders ₹0); 100% eKYC. | Frequency distractor rejection (₹6,000/instalment rejected), beneficiary eligibility (landholder vs tenant). |
| 👷 **MGNREGS** | Rural Employment | Statutory **100 days** unskilled wage employment per rural household; **15-day** work allocation timeline. | Geographic scope (rural only; urban claims flagged as `WRONG_CONTEXT`), applicant household constraints. |
| 🏥 **PM-JAY** | Health Assurance | **₹5,00,000** annual family health cover; secondary/tertiary hospitalisation; **100% cashless**; no family size cap. | Family-level cap enforcement (₹10L claims contradicted), secondary/tertiary inpatient scope. |
| 🏠 **PMAY-G** | Rural Housing | **₹1,20,000** unit grant in plain areas; **₹1,30,000** in hilly/difficult areas; **25 sq. metres** minimum floor area. | Topographic area discrimination (`plains_areas` vs `hilly_areas`), minimum floor area vs plot area. |
| ☀️ **PM-KUSUM** | Solar Agriculture | **60% total capital subsidy** (30% CFA + 30% State); standalone pumps up to **7.5 HP** capacity. | Component-B standalone pump scope, capacity ceiling (7.5 HP), CFA vs combined subsidy alignment. |
| 💼 **PMMY** | Mudra Micro-Credit | **Shishu** (up to ₹50,000), **Kishore** (₹50,000–₹5,00,000), **Tarun** (₹5,00,000–₹10,00,000/₹20,00,000); collateral-free. | Tier threshold boundaries (e.g., claiming ₹1,00,000 under Shishu flagged as `CONTRADICTED`). |
| 📂 **Upload Custom Document** | **Any Policy Document** | **Dynamic Ingestion (PDF / TXT)** with page-level chunking, table extraction, and rule induction. | Page-grounded citations, in-memory RRF hybrid retrieval, zero-shot condition-aware claim verification. |

---

## 2. The Core Problem

Consider a citizen or farmer asking:
> *"For Kharif food grains under PMFBY, what is the maximum farmer premium?"*

A government policy document contains complex tables with distinct rates for different crops, seasons, and jurisdictions:
- **Food grains and oilseeds:** Maximum 2.0% in Kharif, 1.5% in Rabi (subject to *"or Actuarial rate, whichever is less"*).
- **Annual commercial and horticultural crops:** Maximum 5.0% across all seasons.
- **Subsidy sharing:** 90:10 between Centre and North Eastern States; 50:50 in General States.

A standard semantic or keyword-based RAG system retrieves the document and often generates:
> *"Under PMFBY, the farmer premium for Kharif food grains is 5.0% of Sum Insured."*

An ordinary verifier checks whether `5.0%` appears in the retrieved passage and accepts the answer. **The number genuinely occurs in the document, but the claim is completely incorrect.**

### The Grounding Invariant
FieldGuard enforces strict **condition-aware evidence grounding**:
1. Numbers are never evaluated in isolation from their applicable conditions.
2. Direct contradictions are distinguished from evidence belonging to the wrong context (`WRONG_CONTEXT`).
3. Insufficient, ambiguous, or superseded evidence triggers conservative abstention (`UNVERIFIABLE`).

---

## 2. Key Empirical Findings

Evaluated on the held-out PMFBY benchmark ($n = 168$ claims, 114 non-supported claims across 42 claim families) with 1,000-iteration cluster bootstrap resampling:

| System / Baseline | Accuracy | Macro-F1 | False-Support Rate (FSR) | WRONG_CONTEXT FSR | UNVERIFIABLE FSR | Coverage | Verification Latency |
|---|---|---|---|---|---|---|---|
| **Baseline A: Retrieval Only** | 10.71% | 5.08% | 21.05% (24/114) | 23.68% | 45.45% | 14.29% | 0.90 ms |
| **Baseline B: Numeric Only** | 44.64% | 32.35% | 81.58% (93/114) | 100.0% | 90.91% | 98.21% | 2.45 ms |
| **Baseline C: Numeric + Basic Context** | 72.62% | 72.62% | 36.84% (42/114) | 23.68% | 27.27% | 87.50% | 1.28 ms |
| **FieldGuard Full** | **94.05%** | **94.11%** | **2.63% (3/114)** | **0.00%** | **0.00%** | **82.14%** | **1.42 ms** |

*Primary Result:* FieldGuard reduces the false-support rate from **81.58%** in numeric-only and **36.84%** in basic context down to **2.63%**, while maintaining high classification accuracy (**94.05%**) and high answer coverage (**82.14%**).

---

## 3. The Four Primary Verdicts

FieldGuard categorizes claims into four mutually exclusive, deterministic verdict labels:

```mermaid
flowchart TD
    Claim["Candidate Numerical Claim (q, c)"] --> Parse["Claim Parser & Normalizer"]
    Parse --> Retrieve["Hybrid Retrieval (RRF: Semantic + Lexical + Table)"]
    Retrieve --> Match["10-Step Condition Matcher"]
    
    Match --> Cond1{"Sufficient & Applicable Evidence?"}
    Cond1 -- No --> UNVERIFIABLE["UNVERIFIABLE\n(Abstain; Missing/Ambiguous/Superseded)"]
    Cond1 -- Yes --> Cond2{"Context Match?\n(Crop, Season, Geo, Period)"}
    
    Cond2 -- No --> WRONG_CONTEXT["WRONG_CONTEXT\n(Number true in different context)"]
    Cond2 -- Yes --> Cond3{"Value, Operator & Qualifiers Match?"}
    
    Cond3 -- Yes --> SUPPORTED["SUPPORTED\n(Verified under matching context)"]
    Cond3 -- No --> CONTRADICTED["CONTRADICTED\n(Direct contradiction in same context)"]
```

---

## 4. Repository Structure

```text
FieldGuard_ag/
├── pyproject.toml              # Build backend, dependencies, and packaging metadata
├── requirements.txt            # Pinned dependencies
├── README.md                   # Comprehensive project documentation
├── app.py                      # Interactive Streamlit web interface
├── configs/                    # Experiment, parser, and retrieval configurations
├── data/
│   ├── raw/documents/          # Verified official policy documents (PMFBY 2023, 2016, PIB)
│   ├── processed/              # Extracted chunks.jsonl, table_rows.jsonl, extraction report
│   ├── manifests/              # Source manifests (source_manifest.json, download log)
│   └── benchmark/              # Benchmark claims (claims.jsonl, evidence.jsonl, manifest)
├── docs/                       # Comprehensive technical and methodology reports
│   ├── architecture.md         # Full architectural specifications & data flows
│   ├── methodology.md          # Mathematical formulation and experimental protocol
│   ├── data_dictionary.md      # Typed schema dictionary and missing value conventions
│   ├── annotation_guidelines.md# Annotation rules and ambiguous case handling
│   ├── implementation_log.md   # Chronological development and debugging log
│   ├── error_analysis.md       # Root-cause analysis of residual errors
│   ├── ablation_analysis.md    # Single-component ablation study analysis
│   ├── limitations.md          # Methodological, domain, and empirical boundaries
│   ├── reproducibility.md      # Exact instructions for clean environment replication
│   └── research_report.md      # Full MSc Capstone Thesis Research Report
├── experiments/                # Reproducible CLI experiment scripts
│   ├── run_all.py              # Master pipeline runner (Experiments A-I)
│   ├── run_retrieval.py        # Experiment A: Retrieval comparison
│   ├── run_verification.py     # Experiments B-F: Verification & baseline comparison
│   ├── run_ablations.py        # Experiment G: Controlled ablation study
│   └── compare_claim_parsers.py# Experiment H: Claim parser comparison
├── results/                    # Saved evaluation artifacts
│   ├── metrics/                # Metrics CSVs (verification, ablations, recall, MRR)
│   ├── predictions/            # Raw JSONL predictions for all systems and ablations
│   ├── tables/                 # Publication-ready CSV summary tables
│   ├── figures/                # High-resolution comparison plots
│   └── logs/                   # Experiment master log (experiment_master_log.json)
├── src/fieldguard/             # Core Python package
│   ├── cli.py                  # Unified command-line interface
│   ├── claim_parser.py         # Deterministic rule-based claim parser
│   ├── numeric_normalizer.py   # Type-safe numeric & operator normalizer
│   ├── condition_matcher.py    # Structured semantic condition & qualification matcher
│   ├── temporal_resolver.py    # Policy version & temporal applicability engine
│   ├── evidence_schema.py      # Typed dataclass schemas for evidence and claims
│   ├── evidence_store.py       # JSONL evidence store and verified rule repository
│   ├── verdicts.py             # Verdict enum and decision finalization logic
│   ├── verifier.py             # FieldGuardVerifier 10-step verification engine
│   ├── retrieval/              # Semantic, Lexical (BM25), Table, and Hybrid (RRF) retrievers
│   └── evaluation/             # Metrics, bootstrap CIs, ablations, error analysis
└── tests/                      # Automated test suite (51 tests, 100% passing)
```

---

## 5. Quick Start & Installation

### Step 1: Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### Step 2: Run Automated Tests
```powershell
python -m pytest -v
```
All **84 tests pass (100%)** in ~15 seconds without external network dependencies or paid API keys.
Includes 51 PMFBY tests, 13 PM-KISAN tests, 9 flagship/upload tests, and 11 end-to-end Streamlit UI tests.

---

## 6. Command-Line Interface (CLI)

FieldGuard provides a unified command-line interface (`python -m fieldguard.cli`):

### Validate Source Manifest
```powershell
python -m fieldguard.cli sources validate
```

### Build or Refresh Retrieval Indexes
```powershell
python -m fieldguard.cli index build
```

### Retrieve Evidence for a Query
```powershell
python -m fieldguard.cli retrieve --query "What is the maximum farmer premium for Kharif food grains?" --method hybrid
```

### Verify a Numerical Claim End-to-End
```powershell
python -m fieldguard.cli verify --claim "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured."
```

Output:
```text
=== FieldGuard Numerical Claim Verification ===
Claim   : Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.
Verdict : SUPPORTED
Reason  : Claim is SUPPORTED by verified rule RULE_OG2023_PREM_KHARIF_FOOD_OILSEED in EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R1.
Checks  :
  - numeric_match       : PASSED
  - category_match      : PASSED
  - season_match        : PASSED
  - qualification_match : PASSED
  - temporal_match      : PASSED
  - source_authority    : PASSED
Latency : 1.11 ms
Supporting Evidence IDs: EV_DOC_PMFBY_OG_2023_P4_CHUNK_2, EV_DOC_PMFBY_OG_2023_P4_TBL_OG2023_PREMIUM_RATES_R1
```

### Run Evaluation Experiments
```powershell
# Evaluate retrieval quality (Experiment A)
python -m fieldguard.cli evaluate retrieval --split test

# Evaluate verification performance across baselines (Experiments B-F)
python -m fieldguard.cli evaluate verification --split test

# Run single-component ablations (Experiment G)
python -m fieldguard.cli evaluate ablations --split test

# Generate comprehensive error analysis report
python -m fieldguard.cli evaluate errors --split test
```

---

## 7. Interactive Demonstration UI & Live Browser Testing

### Launch Interactive Streamlit Web App
```powershell
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser. The platform provides:
- **🏛️ 7 Flagship Schemes Corpus**: Instant switching between PMFBY, PM-KISAN, MGNREGS, PM-JAY, PMAY-G, PM-KUSUM, and PMMY with pre-loaded benchmark scenarios.
- **📂 Upload Custom Policy Document (PDF / TXT)**:
  - **Natural Language Policy Q&A**: Ask questions in plain English and receive fact-grounded answers with exact physical PDF page and passage citations.
  - **Condition-Aware Verification**: Validate arbitrary numerical claims against uploaded rules with instant verdict badges (`SUPPORTED`, `WRONG_CONTEXT`, `CONTRADICTED`, `UNVERIFIABLE`).
  - **Document Structure Inspector**: Inspect indexed passages, table rows, and induced candidate rules.

### Run Automated Live Browser Tests
```powershell
python scripts/test_live_browser.py
```
Uses **Playwright + Microsoft Edge** to launch a live browser instance, navigate to the running Streamlit server, simulate user interactions, upload test documents, verify verdicts, and save visual proof screenshots to `results/screenshots/`.

---

## 8. License & Attribution

Developed as an MSc Data Science Capstone Research Project. Distributed under the MIT License.
Official PMFBY guidelines and PIB releases are public government documents courtesy of the Ministry of Agriculture & Farmers Welfare and Press Information Bureau, Government of India.

