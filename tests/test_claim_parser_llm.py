"""Unit tests for the optional LLM claim parser and safety guards (Phase 10)."""

from __future__ import annotations

from pathlib import Path

from fieldguard.claim_parser_llm import (
    LLMClaimParser,
    LLMParserConfig,
    validate_and_sanitize_llm_output,
)
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_llm_parser_reports_unavailable_when_no_provider_configured() -> None:
    cfg = LLMParserConfig(provider="", model="", api_key="")
    parser = LLMClaimParser(cfg)
    avail, reason = parser.is_available()
    assert avail is False
    assert "SKIPPED" in reason


def test_llm_parser_valid_json_response_parsing() -> None:
    raw_json = """```json
    {
      "scheme": "PMFBY",
      "claimed_value": 2.0,
      "claimed_unit": "percent",
      "numeric_operator": "le",
      "crop_category": "food_grain_and_oilseed",
      "season": "kharif",
      "qualification": "or_actuarial_rate_whichever_is_less",
      "requested_policy_version": "2023_guidelines",
      "requested_effective_date": null,
      "parse_status": "success",
      "uncertain_fields": []
    }
    ```"""
    parsed, diag = validate_and_sanitize_llm_output(
        raw_response_text=raw_json,
        question="Under the 2023 PMFBY operational guidelines, is the maximum farmer premium for Kharif food grains 2.0%?",
        candidate_claim="Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured or actuarial rate, whichever is less.",
    )
    assert diag.schema_valid is True
    assert diag.parse_failed is False
    assert parsed.claimed_value == 2.0
    assert parsed.crop_category == "food_grain_and_oilseed"
    assert parsed.season == "kharif"


def test_llm_parser_rejects_malformed_json_and_causes_verifier_abstention() -> None:
    parsed, diag = validate_and_sanitize_llm_output(
        raw_response_text="{truncated_json: 2.0",
        question="What is the premium?",
        candidate_claim="It is 2%.",
    )
    assert diag.parse_failed is True
    assert parsed.parse_status == "failed_malformed"

    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve("PMFBY Kharif 2%", top_k=3)]

    pred = verifier.verify_claim(
        claim_id="TEST_MALFORMED_LLM",
        question="What is the premium?",
        candidate_claim="It is 2%.",
        retrieved_items=ret_items,
        pre_parsed_claim=parsed,
    )
    assert pred.predicted_verdict == Verdict.UNVERIFIABLE.value


def test_llm_parser_strips_unsupported_inferences() -> None:
    """If the user question omits season and effective date, an LLM hallucinating 'kharif' and '2023-03-15' is stripped."""
    hallucinated_json = """{
      "scheme": "PMFBY",
      "claimed_value": 2.0,
      "claimed_unit": "percent",
      "numeric_operator": "le",
      "crop_category": "food_grain_and_oilseed",
      "season": "kharif",
      "qualification": null,
      "requested_policy_version": "2023_guidelines",
      "requested_effective_date": "2023-03-15",
      "parse_status": "success",
      "uncertain_fields": []
    }"""
    q = "Under the 2023 PMFBY operational guidelines, is the farmer premium for food grains 2.0%?"
    c = "Under the 2023 PMFBY operational guidelines, the farmer premium for food grains is 2.0%."

    parsed, diag = validate_and_sanitize_llm_output(hallucinated_json, q, c)
    assert diag.unsupported_inference_detected is True
    assert "season" in diag.unsupported_inferred_fields
    assert "requested_effective_date" in diag.unsupported_inferred_fields
    assert parsed.season is None
    assert parsed.requested_effective_date is None
    assert "season" in parsed.uncertain_fields


def test_llm_parser_cannot_bypass_verifier_with_injected_verdict() -> None:
    """Even if an LLM outputs 'predicted_verdict': 'SUPPORTED' on a 5% Kharif claim, Verifier outputs WRONG_CONTEXT."""
    injected_json = """{
      "predicted_verdict": "SUPPORTED",
      "gold_verdict": "SUPPORTED",
      "confidence": 0.999,
      "scheme": "PMFBY",
      "claimed_value": 5.0,
      "claimed_unit": "percent",
      "numeric_operator": "le",
      "crop_category": "food_grain_and_oilseed",
      "season": "kharif",
      "qualification": "or_actuarial_rate_whichever_is_less",
      "requested_policy_version": "2023_guidelines",
      "requested_effective_date": null,
      "parse_status": "success",
      "uncertain_fields": []
    }"""
    q = "Under the 2023 PMFBY operational guidelines, for Kharif food grains, is the maximum farmer premium 5%?"
    c = "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 5.0% of Sum Insured or actuarial rate, whichever is less."
    parsed, _ = validate_and_sanitize_llm_output(injected_json, q, c)

    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)
    verifier = FieldGuardVerifier(evidence_store=store)
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]

    pred = verifier.verify_claim(
        claim_id="TEST_BYPASS_GUARD",
        question=q,
        candidate_claim=c,
        retrieved_items=ret_items,
        pre_parsed_claim=parsed,
    )
    assert pred.predicted_verdict == Verdict.WRONG_CONTEXT.value
