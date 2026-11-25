# Evaluation scope

The application exposes seven scheme adapters. Availability in the UI does not establish equal accuracy across those schemes.

| Evaluation | Scope | Saved result | Interpretation |
|---|---|---|---|
| PMFBY held-out benchmark | 168 claims, 42 families | 94.05% accuracy; 2.63% false support | Curated domain benchmark; held-out family split |
| PM-KISAN held-out benchmark | 40 claims, 10 families | 100.00% accuracy; 0.00% false support | Diagnosed & fixed in Problem 3; beats Baseline C (85.00%) |
| MGNREGA held-out benchmark | 40 test claims (100 total) | 72.50% accuracy; 16.67% false support | Beats Baseline C (60.00% acc, 33.33% FSR) and Baseline A (25.00% acc) |
| PM-JAY held-out benchmark | 40 test claims (100 total) | 77.50% accuracy; 20.00% false support | Beats Baseline C (60.00% acc, 40.00% FSR) and Baseline A (25.00% acc) |
| PMAY-G held-out benchmark | 40 test claims (100 total) | 87.50% accuracy; 0.00% false support | Beats Baseline C (72.50% acc, 20.00% FSR) and Baseline A (25.00% acc) |
| PM-KUSUM held-out benchmark | 40 test claims (100 total) | 90.00% accuracy; 0.00% false support | Beats Baseline C (72.50% acc, 20.00% FSR) and Baseline A (25.00% acc) |
| PMMY held-out benchmark | 40 test claims (100 total) | 90.00% accuracy; 0.00% false support | Beats Baseline C (70.00% acc, 23.33% FSR) and Baseline A (25.00% acc) |
| Seven-scheme demonstration smoke check | 24 curated UI scenarios | 24 match the expected label | All 24 demo scenarios pass with 0 mismatches |
| Custom uploads corpus | 5 documents, 48 labelled claims | 89.58% accuracy; 0.00% false support | 0 false support across prose, tables, lists, multi-column |

Sources: `results/metrics/verification_results.csv`, `results/pm_kisan/tables/verification_comparison.csv`, `results/multi_scheme/summary.csv`, and `results/tables/scheme_smoke.csv`.

Run `python experiments/run_scheme_smoke.py` from the repository root to regenerate the demonstration report. It uses hybrid top-5 retrieval and records every expected/actual label and rationale, including mismatches. Scenario definitions live in `src/fieldguard/demo_scenarios.py` and are shared with the UI. The script reports discrepancies without rewriting expected labels to match the implementation.

The screenshot regression suite additionally exercises Indian-grouped rupee amounts, square metres, horsepower, and the four-component PM-KISAN sentence through hybrid top-5/top-9 retrieval. Changed values and missing or mismatched conditions must not be supported. Streamlit tests enter all five reported built-in claims and click Verify. The full suite passed 179 tests after these changes; the cache revision was then checked with six targeted cache/UI tests. The original uploaded PMFBY 2020 PDF was unavailable, so its yield-threshold paraphrase is covered by equivalent-text fixtures and adversarial variants rather than an end-to-end run against that file.

The five additional schemes still need independently annotated, family-separated benchmarks with representative positive, negative, ambiguous, and temporal cases. Uploads need a separate corpus covering PDF layouts, eligibility, qualifiers, and retrieval failures before any general accuracy claim is justified.

Excerpt search uses a conservative lexical-coverage heuristic. Its threshold is not a calibrated relevance probability, and excerpts may omit information elsewhere in a document. It does not generate answers or verify uploaded provenance.
