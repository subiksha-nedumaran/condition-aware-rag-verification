# FieldGuard — Claim Parser Comparison Analysis (Phase 10)

## 1. Experimental Setup

Phase 10 compares two structured claim parsers that map `(question, candidate_claim)` into the validated `ParsedClaim` schema before passing the structured claim into the unchanged `FieldGuardVerifier`:

- **Parser A (`DeterministicClaimParser`):** Offline deterministic regex and rule-based normalizer (`src/fieldguard/claim_parser.py`).
- **Parser B (`LLMClaimParser`):** Optional LLM-based JSON extractor with strict schema validation and unsupported-inference rejection (`src/fieldguard/claim_parser_llm.py`).

## 2. Parser-Only Field Extraction Metrics (Parser A on Test Split)

| Structured Claim Field | Evaluated Claims ($n$) | Exact Matches | Exact-Match Accuracy |
| :--- | :---: | :---: | :---: |
| `scheme` | 168 | 168 | 1.0000 |
| `claimed_value` | 168 | 168 | 1.0000 |
| `claimed_unit` | 168 | 168 | 1.0000 |
| `numeric_operator` | 168 | 120 | 0.7143 |
| `crop_category` | 168 | 168 | 1.0000 |
| `season` | 168 | 156 | 0.9286 |
| `qualification` | 168 | 156 | 0.9286 |
| `requested_policy_version` | 168 | 168 | 1.0000 |
| `requested_effective_date` | 168 | 168 | 1.0000 |

## 3. End-to-End Verification & Parser Comparison Summary

- **Parser A (`DeterministicClaimParser`):** Status = `SUCCESS` | All-Fields Exact Match = `0.6250` | Schema-Valid Rate = `1.0000` | Unsupported-Inference Rate = `0.0000` | Mean Parse Latency = `1.6856 ms` | End-to-End Verdict Accuracy = `0.5714` | End-to-End Macro-F1 = `0.5529` | End-to-End False-Support Rate = `0.0263`.
- **Parser B (`LLMClaimParser`):** Status = `SKIPPED` | Reason = SKIPPED: Optional LLM provider not configured (FIELDGUARD_LLM_PROVIDER / FIELDGUARD_LLM_MODEL / FIELDGUARD_LLM_API_KEY not set in environment).

## 4. Safety Guarantees Verified in `tests/test_claim_parser_llm.py`

1. **No Verdict Bypass:** `LLMClaimParser` extracts only structured claim fields (`ParsedClaim`); any injected `predicted_verdict` or `gold_verdict` key in the LLM JSON is ignored and cannot bypass `FieldGuardVerifier`.
2. **Malformed JSON Rejection:** Truncated or non-JSON responses are caught and converted to `parse_status='failed_malformed'`, causing `FieldGuardVerifier` to abstain (`UNVERIFIABLE`) rather than emit a false support.
3. **Unsupported Inference Rejection:** `detect_unsupported_llm_inferences` strips hallucinated crop categories, seasons, or effective dates that do not appear in the user's question or claim, preserving `uncertain_fields`.
