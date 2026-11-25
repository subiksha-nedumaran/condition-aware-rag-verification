# FieldGuard website test report

Date: 30 October 2026 (Asia/Calcutta)
Target: C:/FieldGuard_ag; live website http://localhost:8501

## Result

**Automated suite: 179 passed, 0 failed, in 38.65 seconds. Live-browser acceptance: incomplete.** Do not interpret passing automated tests as proof of production readiness or policy accuracy.

## Checks executed

| Check | Result |
|---|---|
| Full pytest suite, including Streamlit AppTest | PASS — 179 tests |
| Live Streamlit health endpoint | PASS — returned `ok` |
| Installed dependency consistency (`pip check`) | PASS — no broken requirements |
| Edge desktop homepage | PASS — FieldGuard heading and scheme prompt rendered; screenshot saved |
| Existing live-browser automation | FAIL — navigation selector returned zero labels immediately after homepage load |
| Follow-up Edge navigation | INCOMPLETE — PM-KISAN radio input click timed out because surrounding elements intercepted pointer events |

## Automated coverage

- Website startup, all eight navigation modes, scheme switching, empty-input feedback, Q&A tab, document upload, and verification results.
- Five screenshot-reported custom claims entered through the Streamlit UI: PM-KISAN, PM-JAY, PMAY-G, PM-KUSUM, and PMMY.
- Indian currency grouping, square-metre and horsepower units; multi-number PM-KISAN components and wrong-value variants.
- Retrieval grounding, numerical normalization, condition matching, temporal checks, provenance, benchmark integrity, baseline/ablation behavior, and CLI tests.
- Upload trust boundaries, beneficiaries, bounds, frequency, geography, conflicts, omitted conditions, and missing retrieval.
- Empty, malformed, encrypted, image-only PDFs and invalid text encoding; per-session caching and invalidation; model setup errors; excerpt relevance filtering.

The original uploaded PMFBY 2020 PDF remains unavailable. Equivalent-text fixtures test its yield-threshold paraphrase; the exact PDF extraction and retrieval path is unverified.

## Findings and priorities

1. **Live-browser test reliability needs repair.** The shipped script queries labels before proving navigation readiness and expects the obsolete “Grounded Answer” heading. It also contains a skip path followed by an unconditional “100% passed” message. Its result is not a reliable release gate.
2. **Live radio-control interaction needs investigation.** Playwright resolved the PM-KISAN input but reported intercepted pointer events. This may be a custom-control locator issue; this run does not establish that ordinary human clicks fail. Test the visible label/keyboard interaction before diagnosing an application defect.
3. **Uploaded verification remains deliberately limited.** Arbitrary paraphrases and complex tables are not generally supported. Non-numerical statements receive guidance to use excerpt search.
4. **Accuracy claims must retain their scope.** The previously generated seven-scheme smoke report matched 24/24 curated examples; it was not rerun in this audit and is not a held-out accuracy estimate. Saved historical PMFBY and PM-KISAN metrics likewise do not certify current arbitrary-query behavior.

## Not covered / remaining acceptance work

- Complete live-browser navigation, file upload, and result interaction after resolving locator issues.
- Mobile/tablet layout, keyboard-only accessibility, screen readers, cross-browser compatibility, and visual layout review.
- Concurrent-user load, large-file performance, adversarial security/penetration testing, and deployment configuration.
- Real scanned-document OCR (not implemented), representative arbitrary-document accuracy, and current government-policy validation.

## Artifacts

- `results/logs/website_test_junit.xml`: machine-readable full-suite results.
- `results/logs/live_browser_test.txt`: original live-browser failure log.
- `results/screenshots/website_audit_desktop.png`: live desktop capture (captured, not visually reviewed).
- `results/tables/scheme_smoke.csv`: previous seven-scheme scenario report.

## Test inventory

| Test module | Cases |
|---|---:|
| test_ablation | 5 |
| test_claim_parser_llm | 5 |
| test_cli | 6 |
| test_condition_matching | 4 |
| test_data_integrity | 3 |
| test_end_to_end | 3 |
| test_flagship_schemes | 9 |
| test_numeric_normalization | 8 |
| test_pm_kisan_verification | 9 |
| test_regressions | 3 |
| test_retrieval_metrics | 3 |
| test_retrieved_evidence_grounding | 5 |
| test_schema_generalization | 4 |
| test_screenshot_verification | 34 |
| test_streamlit_app | 16 |
| test_temporal_resolution | 4 |
| test_upload_medium_fixes | 13 |
| test_uploaded_rules | 15 |
| test_uploaded_verification | 28 |
| test_verdicts | 2 |
