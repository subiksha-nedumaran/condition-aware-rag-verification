# FieldGuard Reproducibility Protocol

This document provides complete, deterministic instructions to install, verify, test, and reproduce all empirical results and artifacts of FieldGuard from a clean environment.

---

## 1. System Requirements & Environment

- **Operating System:** Windows 10/11 x64, Linux (Ubuntu 20.04+), or macOS (12.0+).
- **Python Version:** Python >= 3.11 (Validated on CPython 3.14.3 x64).
- **Hardware Requirements:**
  - CPU: Standard multi-core x86_64 CPU (no GPU required).
  - RAM: Minimum 4 GB (8 GB recommended).
  - Disk Space: ~1.5 GB (including embedding weights and dependencies).
- **Network Requirements:** None for core deterministic verification, unit tests, and experiments. All test fixtures, documents, models, and embeddings run strictly offline.

---

## 2. Installation and Virtual Environment Setup

### Step 1: Create and Activate Virtual Environment
```powershell
# From project root C:\FieldGuard_ag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Package in Editable Mode
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Verify installed packages:
```powershell
python -c "import fieldguard; print(fieldguard.__file__)"
```

---

## 3. Automated Test Suite Execution

Run the complete 51-test automated suite:
```powershell
python -m pytest -v
```

Expected output:
```text
============================= 51 passed in 3.26s ==============================
```

To run individual test groups:
- **Condition Matching:** `pytest tests/test_condition_matching.py -v`
- **Numerical Normalization:** `pytest tests/test_numeric_normalization.py -v`
- **Adversarial Regressions:** `pytest tests/test_regressions.py -v`
- **Unified CLI:** `pytest tests/test_cli.py -v`
- **End-to-End Pipelines:** `pytest tests/test_end_to_end.py -v`

---

## 4. Reproducing Data Ingestion and Indexing

```powershell
# Validate source manifest and file checksums
python -m fieldguard.cli sources validate

# Execute acquisition and document/table extraction
python -m fieldguard.cli ingest

# Build lexical, semantic embedding, and table retrieval indexes
python -m fieldguard.cli index build
```

---

## 5. Reproducing Experiments

All experiments use fixed seed `42` and cluster bootstrap iterations (1,000 for verification, 500 for ablations).

### Experiment A: Retrieval Evaluation
```powershell
python -m fieldguard.cli evaluate retrieval --split test
```
*Outputs:*
- `results/metrics/recall_at_k.csv`
- `results/metrics/mrr.csv`
- `results/tables/retrieval_comparison.csv`
- `results/predictions/retrieval_rankings.jsonl`

### Experiments B through F: Verification Performance & Baselines
```powershell
python -m fieldguard.cli evaluate verification --split test --bootstrap-iterations 1000
```
*Outputs:*
- `results/metrics/verification_results.csv`
- `results/tables/verification_comparison.csv`
- `results/tables/false_support_breakdown.csv`
- `results/tables/context_perturbations.csv`
- `results/tables/temporal_grounding.csv`
- `results/predictions/verification_predictions.jsonl`

### Experiment G: Controlled Ablation Study
```powershell
python -m fieldguard.cli evaluate ablations --split test --bootstrap-iterations 500
```
*Outputs:*
- `results/metrics/ablation_results.csv`
- `results/tables/ablation_comparison.csv`
- `results/predictions/ablation_predictions.jsonl`
- `results/figures/ablation_comparison.png`

### Experiment H: Claim Parser Comparison
```powershell
python experiments/compare_claim_parsers.py --split test
```
*Outputs:*
- `results/metrics/claim_parser_comparison.csv`
- `results/tables/claim_parser_field_metrics.csv`
- `results/predictions/claim_parser_predictions.jsonl`

### Comprehensive Error Analysis
```powershell
python -m fieldguard.cli evaluate errors --split test
```
*Outputs:*
- `docs/error_analysis.md`

### Master Pipeline (All Experiments in One Command)
```powershell
python experiments/run_all.py
```
*Outputs:*
- `results/logs/experiment_master_log.json`

---

## 6. Interactive Web Demonstration (Optional)
```powershell
pip install streamlit
streamlit run app.py
```
Opens interactive UI at `http://localhost:8501`.

