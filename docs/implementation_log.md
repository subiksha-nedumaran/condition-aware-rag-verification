# Complete Implementation, Audit, and Evolution Log

## Project Identity
- **Project Title:** Condition-Aware Verification of Numerical Claims in Government-Scheme Question Answering Using Retrieval-Augmented Generation (RAG)
- **Primary Domain:** Data Science, NLP, Information Retrieval, Fact Verification, AI Safety
- **Core Scheme:** Pradhan Mantri Fasal Bima Yojana (PMFBY), Ministry of Agriculture & Farmers Welfare, Government of India.
- **Repository Root:** `C:\FieldGuard_ag`
- **Execution Platform:** Python 3.14.3, Windows x64, Isolated Virtual Environment (`.venv`)

---

## Phase 0: Initial Archive Audit & Foundation Verification (2026-10-29 / 2026-10-30)

### 1. Workspace Discovery
- **Source Artifact:** Extracted from the original project archive.
- **Target Workspace:** Established at `C:\FieldGuard_ag`.
- **Git Repository:** Initialized Git repository in `C:\FieldGuard_ag`, tracked all baseline code, configs, processed corpora, and historical results.
- **Dependency Audit:**
  - Audited all dependencies in `requirements.txt` and `pyproject.toml`.
  - Python version: Python 3.14.3.
  - Successfully created virtual environment `.venv` and installed pinned dependencies (`numpy`, `pandas`, `scikit-learn`, `scipy`, `matplotlib`, `seaborn`, `pyyaml`, `requests`, `tqdm`, `safetensors`, `tokenizers`, `huggingface-hub`, `pytest`).
  - Successfully resolved packaging configuration in `pyproject.toml` and verified editable installation (`pip install -e .`).

### 2. Baseline Test Execution & Initial Findings
- Full automated test suite executed with `pytest`:
  - **43 tests passed, 2 failed** out of 45 tests.
  - Failed Test 1: `tests/test_condition_matching.py::test_correct_number_wrong_geography` (`AssertionError: assert False is True` on `res.is_wrong_context_for_matched_number`).
  - Failed Test 2: `tests/test_regressions.py::test_regression_pib_dec2025_supports_100_percent_state_subsidy_for_wild_animal_addon` (`AssertionError: assert 'CONTRADICTED' == 'SUPPORTED'`).
- Historical Metrics Recorded in Repository:
  - Accuracy: 31.55%
  - Macro-F1: 27.11%
  - False-Support Rate: 0.0% (0/114)
  - Coverage: 19.05% (Abstention rate: 80.95%)
  - High abstention rate was primarily caused by the condition-matching failures identified in the test suite.

---

## Phase 1 & 2: Root-Cause Investigation of Condition-Matching Defect

### 1. Detailed Investigation of Test Failures
- Investigated `test_correct_number_wrong_geography`:
  - Question: *"Under the 2023 PMFBY operational guidelines, is the Central Government's share of normal premium subsidy 90.0% in General States?"*
  - Claim: *"Under the 2023 PMFBY operational guidelines, the Central Government's share of normal premium subsidy is 90.0% in General States."*
  - Matched Rule: `RULE_OG2023_SUBSIDY_SHARE_NER_STATES` (Central Government share is 90% in North Eastern States, whereas in General States it is 50%).
  - Expected Verdict: `WRONG_CONTEXT` because 90% is true for NER States, not General States.
  - Actual Output: Evaluated as `is_wrong_context = False` because `res.operator_match` was `False` (`mismatch_reasons: ['operator_mismatch(claimed=lt, rule=eq)']`).
- Investigated `test_regression_pib_dec2025_supports_100_percent_state_subsidy_for_wild_animal_addon`:
  - Question: *"According to the December 2025 PIB press release (PRID=2197713), what share of the cost is borne by the State Government when notifying wild animal attack as an add-on cover under PMFBY?"*
  - Claim: *"According to the December 2025 PIB press release (PRID=2197713), wild animal attack add-on cover under PMFBY is implemented 100.0% at the cost of the respective State Government."*
  - Matched Rule: `RULE_PIB2025_WILD_ANIMAL_STATE_COST` (100% borne by State Government).
  - Expected Verdict: `SUPPORTED`.
  - Actual Output: `CONTRADICTED` with reason `operator_mismatch(claimed=lt, rule=eq)`.

### 2. Root Cause Discovery in `extract_numeric_operator`
- Traced `numeric_operator` extraction in `src/fieldguard/numeric_normalizer.py`:
  ```python
  # Original line 225:
  if re.search(r"\b(?:less\s+than|below|under)\b|<", t):
      return "lt", claims_unconditional
  ```
- **The Defect:** In English policy text and question answering, the preposition *"under"* almost universally appears in administrative phrases such as:
  - *"Under the 2023 PMFBY operational guidelines..."*
  - *"add-on cover under PMFBY..."*
  - *"under Section 4..."*
  - *"under general states..."*
- Because the regex used bare word boundary `\bunder\b`, **any sentence beginning with or mentioning "under the guidelines" or "under PMFBY" was unconditionally parsed as having comparison operator `lt` (`<`)!**
- Because official government rules define exact rates or maximum caps (`eq` or `le`), claims parsed with `lt` failed the operator match (`operator_mismatch(claimed=lt, rule=eq)`), preventing `is_wrong_context` from being recognized in adversarial geographic tests, and causing true supported claims to be incorrectly marked as `CONTRADICTED`.
- This single defect explained both test failures and the depressed baseline coverage (19.05%).

### 3. Engineering Fix
- Modified `src/fieldguard/numeric_normalizer.py` line 225:
  ```python
  # Corrected condition-aware operator extraction:
  if re.search(r"\b(?:less\s+than|strictly\s+less\s+than|below)\b|\bunder\s+(?:\d|₹|one|two|three|four|five)|<", t):
      return "lt", claims_unconditional
  ```
- "Under" is now only treated as an inequality operator (`<`) when it is directly followed by a numerical value, currency, or numeric word token (e.g. *"under 2%"*, *"under ₹50,000"*, *"under 14 days"*). Prepositional context clauses (*"Under the 2023 PMFBY guidelines"*, *"under PMFBY"*) correctly preserve the default exact operator (`eq`).
- **Regression Verification:**
  - `test_correct_number_wrong_geography`: **PASSED** (`is_wrong_context: True`).
  - `test_regression_pib_dec2025_supports_100_percent_state_subsidy_for_wild_animal_addon`: **PASSED** (`predicted_verdict: SUPPORTED`).
  - Full test suite passed: **45 passed, 0 failed in 3.28s**.

---

## Phase 3: Unified CLI Architecture & Test Expansion

### 1. Unified CLI Implementation (`src/fieldguard/cli.py`)
- Implemented full command-line interface supporting all workflows defined in Section 18:
  1. `sources validate`: Validates source manifest JSON/CSV, checks local file presence, validates SHA-256 digests.
  2. `ingest`: Runs acquisition and extraction pipelines.
  3. `index build`: Refreshes BM25, semantic embedding cache, and table retrieval indexes.
  4. `retrieve`: Evaluates query retrieval across hybrid, semantic, lexical, or table modes.
  5. `verify`: Performs end-to-end claim verification and returns standardized JSON/text report with condition checks.
  6. `evaluate`: Dispatches `retrieval`, `verification`, `ablations`, and `errors`.

### 2. CLI Automated Test Suite (`tests/test_cli.py`)
- Created dedicated test module testing all CLI subcommands (`cmd_sources_validate`, `cmd_index_build`, `cmd_retrieve`, `cmd_verify`, `cmd_evaluate`).
- **Test Suite Total:** Expanded from 45 to **51 automated tests**.
- **Execution Result:** **51 passed, 0 failed** in 3.26s.

---

## Phase 4: Full Empirical Evaluation & Results Regeneration

Following the bug fix, all experiments were re-executed using `experiments/run_all.py` on the held-out test split (168 claims, 114 non-supported, 54 supported):

### 1. Retrieval Quality (Experiment A)
| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Item Recall@5 | MRR | Mean Latency (ms) |
|---|---|---|---|---|---|---|---|
| Semantic (`all-MiniLM-L6-v2`) | 0.6914 | 0.9136 | 0.9444 | 0.9630 | 0.8385 | 0.8093 | 50.94 |
| Lexical (BM25) | 0.6728 | 0.9568 | 0.9815 | 1.0000 | 0.8313 | 0.8074 | 0.53 |
| Table-aware | 0.7284 | 0.9383 | 0.9815 | 1.0000 | 0.8488 | 0.8433 | 15.79 |
| **Hybrid (RRF Fusion)** | **0.6914** | **0.9259** | **0.9815** | **0.9815** | **0.9115** | **0.8197** | 16.88 |

*Key finding:* Hybrid retrieval achieved **91.15% item-level recall@5**, substantially outperforming semantic-only retrieval (83.85%) and lexical-only retrieval (83.13%).

### 2. Verification Performance & Baselines (Experiment B & C)
Evaluated on 168 held-out test claims (114 non-supported claims):

| Method | Accuracy | Macro-F1 | False-Support Rate (FSR) | FSR Count | Coverage | Abstention Rate |
|---|---|---|---|---|---|---|
| Baseline A: Retrieval Only | 10.71% | 5.08% | 21.05% | 24 / 114 | 14.29% | 85.71% |
| Baseline B: Numeric Only | 44.64% | 32.35% | 81.58% | 93 / 114 | 98.21% | 1.79% |
| Baseline C: Numeric + Basic Context | 72.62% | 72.62% | 36.84% | 42 / 114 | 87.50% | 12.50% |
| **FieldGuard Full** | **94.05%** | **94.11%** | **2.63%** | **3 / 114** | **82.14%** | **17.86%** |

*Per-Class F1 for Proposed System (Full):*
- `SUPPORTED` F1: **0.9444** (51 True Positives, 3 False Contradictions)
- `CONTRADICTED` F1: **0.9176** (39 True Positives, 3 False Supports, 1 Wrong Context)
- `WRONG_CONTEXT` F1: **0.9500** (38 True Positives, 0 False Supports)
- `UNVERIFIABLE` F1: **0.9524** (30 True Positives, 3 Wrong Contexts)

*False-Support Rate by Category:*
- Wrong-Context FSR: **0.0% (0 / 38)** — FieldGuard prevented 100% of wrong-crop, wrong-season, and wrong-geography false supports.
- Unverifiable FSR: **0.0% (0 / 33)** — FieldGuard never accepted claims lacking sufficient evidence.
- Contradicted FSR: **6.98% (3 / 43)** — Residual false supports limited to borderline distractor edge cases.

### 3. Controlled Ablation Study (Experiment G)
| Ablation Configuration | Accuracy | Macro-F1 | False-Support Rate (FSR) | $\Delta$ FSR vs Full | 95% CI Excludes 0? |
|---|---|---|---|---|---|
| **Full FieldGuard** | **94.05%** | **94.11%** | **2.63% (3/114)** | **0.00%** | Baseline |
| No Structured Condition Matching | 52.38% | 49.41% | 58.77% (67/114) | +56.14% | **Yes (p < 0.001)** |
| No Crop Category Matching | 86.90% | 86.81% | 12.28% (14/114) | +9.65% | **Yes (p < 0.01)** |
| No Season Matching | 91.07% | 91.32% | 7.02% (8/114) | +4.39% | **Yes (p < 0.05)** |
| No Qualification Matching | 92.26% | 92.51% | 7.89% (9/114) | +5.26% | **Yes (p < 0.05)** |
| No Evidence Sufficiency | 33.93% | 20.82% | 89.47% (102/114) | +86.84% | **Yes (p < 0.001)** |
| Baseline Numeric Only | 44.64% | 32.35% | 81.58% (93/114) | +78.95% | **Yes (p < 0.001)** |
| Baseline Basic Context | 72.62% | 72.62% | 36.84% (42/114) | +34.21% | **Yes (p < 0.001)** |

---

## Phase 5: Streamlit Interactive Interface (`app.py`)
- Developed a lightweight interactive web UI using Streamlit (`app.py`).
- Directly interfaces with `build_default_evidence_store`, `build_all_retrievers`, and `FieldGuardVerifier`.
- Features interactive sample scenario selection (covering all 4 canonical verdicts), condition-by-condition check badge breakdown, latency reporting, and expandable retrieved evidence chunks.

---

## Phase 6: Stage 2 Multi-Scheme Generalization & PM-KISAN Evaluation
- Generalized the typed evidence schema (`StructuredRuleRecord`, `ExtractedEvidenceUnit`) to decouple from crop/insurance-specific terminology (`primary_value`, `rule_parameter`, `entity_scope`).
- Built modular Scheme Plugin Architecture in `src/fieldguard/schemes/` (`BaseScheme`, `SchemeRegistry`, `PMFBYScheme`, `PMKisanScheme`).
- Created authoritative PM-KISAN evidence store (`build_pm_kisan_evidence_store`) grounded in official guidelines (Clause 3.1, Clause 5, 2019 launch & universal revision eras).
- Curated and validated independent held-out PM-KISAN benchmark ($n = 26$ claims, 14 non-supported distractors).
- Evaluated zero-shot cross-scheme transfer: FieldGuard achieved **92.31% Accuracy**, **91.95% Macro-F1**, and **0.00% False-Support Rate** on PM-KISAN, drastically outperforming Baselines (Numeric Only FSR: 71.43%).
- Increased regression test suite to **64 / 64 passing (100%)**.

---

## Phase 7: Stage 3 Flagship Schemes Suite & Dynamic Document Ingestion Engine
- Implemented adapters and verified rule corpora for 5 additional flagship national welfare schemes:
  - **MGNREGS**: 100 days statutory wage employment, 15-day work allocation timeline, unemployment allowance.
  - **PM-JAY**: ₹5,00,000 annual family health cover, 100% cashless treatment, no family size limit.
  - **PMAY-G**: ₹1,20,000 plain areas grant, ₹1,30,000 hilly areas grant, 25 sq.m minimum area, SBM toilet aid.
  - **PM-KUSUM**: 60% total capital subsidy (30% CFA + 30% State), 7.5 HP max standalone solar pump capacity.
  - **PMMY**: Shishu (up to ₹50k), Kishore (₹50k-₹5L), Tarun (₹5L-₹10L/₹20L) collateral-free micro-credit.
- Developed the **Dynamic Document Ingestion Engine** (`uploaded_doc_engine.py`):
  - In-memory PDF and TXT guidelines parser using `pypdf`.
  - Block text chunking and table row extraction.
  - Automated candidate rule induction with page-and-value scoped parameter naming (`rule_p{page}_{unit}_{val}`) preventing false conflicts.
  - Implemented `answer_question_from_uploaded_doc` providing grounded answers with physical PDF page numbers and paragraph citations.
- Revamped the Streamlit interactive web platform (`app.py`):
  - Sidebar with all 7 flagship schemes + dedicated "Upload Custom Scheme Document" mode.
  - Three specialized tabs under upload mode: (1) Natural Language Q&A, (2) Condition-Aware Verification, (3) Document Structure Inspector.
  - Fixed scenario dropdown state synchronization and `pre_tab_qa_q` session state handling.
- Automated Testing Expansion:
  - Added `tests/test_flagship_schemes.py` covering registry, flagship adapters, and uploaded document verification.
  - Added `tests/test_streamlit_app.py` using official `streamlit.testing.v1.AppTest` for headless UI verification.
  - Built `scripts/test_live_browser.py` using **Playwright with Microsoft Edge** for live browser verification against `http://localhost:8501`.
- Total test count reached: **84 / 84 passing (100%)**.

---

## Current Status Summary
- **Foundation:** Universal, modular, multi-scheme verification and Q&A framework.
- **Automated Tests:** **84 / 84 passing (100%)** in ~15.2 seconds.
- **Web Interface:** Live and healthy on `http://localhost:8501`.
- **Live Browser Automation:** 100% verified via Playwright on headless Microsoft Edge with visual screenshot captures in `results/screenshots/`.
- **Thesis & Defense Readiness:** Complete, fully documented, verified, and ready for MSc viva defense.
