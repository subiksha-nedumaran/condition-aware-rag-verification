"""Core FieldGuard condition-aware numerical claim verification pipeline (Section 10.6)."""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from fieldguard.claim_parser import DeterministicClaimParser, ParsedClaim
from fieldguard.condition_matcher import (
    ConditionMatchConfig,
    RuleMatchResult,
    check_unstructured_chunk_numeric_distractor,
    evaluate_rule_against_claim,
)
from fieldguard.evidence_store import EvidenceStore
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import compare_numeric_values, extract_all_numeric_mentions
from fieldguard.verdicts import Verdict


@dataclass
class VerifierConfig:
    """Configuration for FieldGuardVerifier supporting full verification, baselines, and ablations."""

    config_name: str = "fieldguard_full"
    mode: str = "fieldguard"  # 'fieldguard', 'retrieval_only', 'numeric_only', 'numeric_basic_context'
    enable_structured_condition_matching: bool = True
    enable_crop_category_matching: bool = True
    enable_season_matching: bool = True
    enable_qualification_matching: bool = True
    enable_temporal_checks: bool = True
    enable_provenance_validation: bool = True
    enable_evidence_sufficiency: bool = True
    retrieval_method: str = "hybrid"
    top_k: int = 5
    retrieval_only_min_score: float = 0.10


@dataclass
class VerificationPrediction:
    """Standardized output schema required by Section 10.7."""

    claim_id: str
    predicted_verdict: str
    parsed_claim: dict[str, Any]
    matched_evidence_ids: list[str]
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    context_mismatch: list[str]
    temporal_status: str
    verification_rationale: str
    abstention_reason: str | None
    retrieval_method: str
    latency_ms: float
    verification_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    config_name: str = "fieldguard_full"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FieldGuardVerifier:
    """
    Deterministic, condition-aware verifier for numerical claims in government-scheme RAG.
    Executes the 10-step verification sequence specified in Section 10.6.
    """

    def __init__(
        self,
        evidence_store: EvidenceStore,
        config: VerifierConfig | None = None,
        parser: Any | None = None,
    ) -> None:
        self.store = evidence_store
        self.config = config or VerifierConfig()
        self.parser = parser or DeterministicClaimParser()

    def verify_claim(
        self,
        claim_id: str,
        question: str,
        candidate_claim: str,
        retrieved_items: list[dict[str, Any]],
        retrieval_method: str | None = None,
        retrieval_latency_ms: float = 0.0,
        pre_parsed_claim: ParsedClaim | None = None,
    ) -> VerificationPrediction:
        """
        Execute verification on a candidate numerical claim given retrieved evidence items.
        """
        t0 = time.perf_counter()
        ret_method = retrieval_method or self.config.retrieval_method

        # Step 1: Parse the question and candidate claim
        parsed = (
            pre_parsed_claim
            if pre_parsed_claim is not None
            else self.parser.parse(question=question, candidate_claim=candidate_claim)
        )

        # Validate retrieved evidence IDs against the evidence store (never invent citations)
        valid_units: list[ExtractedEvidenceUnit] = []
        invalid_ev_ids: list[str] = []
        max_ret_score = 0.0

        for item in retrieved_items:
            ev_id = item.get("evidence_id", "")
            score = float(item.get("retrieval_score", 0.0))
            if score > max_ret_score:
                max_ret_score = score
            unit = self.store.get_evidence_unit(ev_id)
            if unit is None:
                invalid_ev_ids.append(ev_id)
            else:
                valid_units.append(unit)

        matched_ev_ids = [u.evidence_id for u in valid_units]

        # Dispatch to comparison baseline if configured
        if self.config.mode == "retrieval_only":
            pred = self._run_baseline_a_retrieval_only(
                claim_id=claim_id,
                parsed=parsed,
                valid_units=valid_units,
                max_ret_score=max_ret_score,
                ret_method=ret_method,
            )
        elif self.config.mode == "numeric_only":
            pred = self._run_baseline_b_numeric_only(
                claim_id=claim_id,
                parsed=parsed,
                valid_units=valid_units,
                ret_method=ret_method,
            )
        else:
            pred = self._run_fieldguard_pipeline(
                claim_id=claim_id,
                parsed=parsed,
                valid_units=valid_units,
                invalid_ev_ids=invalid_ev_ids,
                ret_method=ret_method,
            )

        ver_ms = (time.perf_counter() - t0) * 1000.0
        pred.verification_latency_ms = round(ver_ms, 4)
        pred.retrieval_latency_ms = round(float(retrieval_latency_ms), 4)
        pred.latency_ms = round(float(retrieval_latency_ms) + ver_ms, 4)
        pred.matched_evidence_ids = matched_ev_ids
        pred.config_name = self.config.config_name
        return pred

    def _run_baseline_a_retrieval_only(
        self,
        claim_id: str,
        parsed: ParsedClaim,
        valid_units: list[ExtractedEvidenceUnit],
        max_ret_score: float,
        ret_method: str,
    ) -> VerificationPrediction:
        """
        Baseline A — Deterministic retrieval-acceptance baseline without FieldGuard verification.
        Accepts the candidate claim as SUPPORTED whenever at least one passage is retrieved above
        a minimal retrieval score threshold, illustrating ordinary unverified RAG acceptance.
        """
        if not valid_units or max_ret_score < self.config.retrieval_only_min_score:
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.UNVERIFIABLE.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                context_mismatch=[],
                temporal_status="unverified_retrieval_baseline",
                verification_rationale="Baseline A (Retrieval without verification): No evidence retrieved.",
                abstention_reason="empty_retrieval",
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        top_unit = valid_units[0]
        return VerificationPrediction(
            claim_id=claim_id,
            predicted_verdict=Verdict.SUPPORTED.value,
            parsed_claim=parsed.to_dict(),
            matched_evidence_ids=[u.evidence_id for u in valid_units],
            supporting_evidence_ids=[top_unit.evidence_id],
            contradicting_evidence_ids=[],
            context_mismatch=[],
            temporal_status="unverified_retrieval_baseline",
            verification_rationale=(
                f"Baseline A (Deterministic Retrieval-Acceptance without Verification): "
                f"Accepted candidate claim based on top retrieved passage {top_unit.evidence_id} "
                f"({top_unit.document_id}, page {top_unit.physical_pdf_page})."
            ),
            abstention_reason=None,
            retrieval_method=ret_method,
            latency_ms=0.0,
        )

    def _run_baseline_b_numeric_only(
        self,
        claim_id: str,
        parsed: ParsedClaim,
        valid_units: list[ExtractedEvidenceUnit],
        ret_method: str,
    ) -> VerificationPrediction:
        """
        Baseline B — Numeric-only matching baseline.
        Checks whether the claimed number appears in any retrieved passage without enforcing
        semantic context, crop category, season, denominator, qualification, or policy version.
        """
        if not valid_units or parsed.claimed_value is None:
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.UNVERIFIABLE.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                context_mismatch=[],
                temporal_status="numeric_only_baseline",
                verification_rationale="Baseline B (Numeric-only): Missing retrieved evidence or claimed number.",
                abstention_reason="missing_evidence_or_number",
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        supporting_ids: list[str] = []
        other_number_ids: list[str] = []

        for unit in valid_units:
            mentions = extract_all_numeric_mentions(unit.text)
            if not mentions:
                continue
            found_num = False
            for m in mentions:
                # Numeric-only baseline checks raw numerical equality or canonical equality
                if abs(m.value - parsed.claimed_value) < 1e-6 or (
                    parsed.canonical_value is not None and abs(m.canonical_value - parsed.canonical_value) < 1e-6
                ):
                    found_num = True
                    break
            if found_num:
                supporting_ids.append(unit.evidence_id)
            else:
                other_number_ids.append(unit.evidence_id)

        if supporting_ids:
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.SUPPORTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=[],
                context_mismatch=[],
                temporal_status="numeric_only_baseline",
                verification_rationale=(
                    f"Baseline B (Numeric-Only Matching): Claimed number {parsed.claimed_value} "
                    f"found in retrieved evidence {supporting_ids}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        if other_number_ids:
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.CONTRADICTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=other_number_ids,
                context_mismatch=[],
                temporal_status="numeric_only_baseline",
                verification_rationale=(
                    f"Baseline B (Numeric-Only Matching): Claimed number {parsed.claimed_value} "
                    f"did not appear in retrieved evidence {other_number_ids}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        return VerificationPrediction(
            claim_id=claim_id,
            predicted_verdict=Verdict.UNVERIFIABLE.value,
            parsed_claim=parsed.to_dict(),
            matched_evidence_ids=[u.evidence_id for u in valid_units],
            supporting_evidence_ids=[],
            contradicting_evidence_ids=[],
            context_mismatch=[],
            temporal_status="numeric_only_baseline",
            verification_rationale="Baseline B (Numeric-Only Matching): No numerical mentions in retrieved text.",
            abstention_reason="no_numbers_in_retrieved_evidence",
            retrieval_method=ret_method,
            latency_ms=0.0,
        )

    def _finalize_verdict(
        self,
        raw_verdict: Verdict,
        abstention_reason: str | None,
        supporting_ids: list[str],
        contradicting_ids: list[str],
        valid_units: list[ExtractedEvidenceUnit],
    ) -> tuple[str, str | None]:
        """
        Handle the evidence-sufficiency / abstention gate (Step 8).
        When `enable_evidence_sufficiency` is False (Ablation 8), the verifier is prohibited
        from abstaining (returning UNVERIFIABLE) and instead defaults to accepting SUPPORTED
        if any retrieved unit exists (or CONTRADICTED if none), demonstrating why explicit
        evidence-sufficiency / abstention logic is essential to prevent false support on
        unverifiable / ambiguous / missing-evidence queries.
        """
        if self.config.enable_evidence_sufficiency:
            return raw_verdict.value, abstention_reason

        if raw_verdict == Verdict.UNVERIFIABLE:
            if valid_units:
                supporting_ids.append(valid_units[0].evidence_id)
                return Verdict.SUPPORTED.value, None
            return Verdict.CONTRADICTED.value, None
        return raw_verdict.value, None

    def _run_fieldguard_pipeline(
        self,
        claim_id: str,
        parsed: ParsedClaim,
        valid_units: list[ExtractedEvidenceUnit],
        invalid_ev_ids: list[str],
        ret_method: str,
    ) -> VerificationPrediction:
        """
        Execute the 10-step FieldGuard verification pipeline (with configurable ablation switches).
        """
        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []
        context_mismatches: list[str] = []

        # Check malformed claim or missing primary numerical value
        if parsed.parse_status == "failed_malformed" or parsed.claimed_value is None or parsed.claimed_unit is None:
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                "malformed_or_non_numerical_claim",
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=contradicting_ids,
                context_mismatch=[],
                temporal_status="not_evaluated_malformed_claim",
                verification_rationale=(
                    "Claim parsing failed or numeric value/unit is corrupted/missing; "
                    "malformed claims cannot bypass verification."
                ),
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check if required contextual fields are uncertain/unspecified when condition matching is enabled
        if self.config.enable_structured_condition_matching:
            missing_context: list[str] = []
            if parsed.scheme is None:
                missing_context.append("scheme")
            if parsed.rule_parameter == "farmer_premium_rate":
                if self.config.enable_crop_category_matching and parsed.crop_category is None:
                    missing_context.append("crop_category")
                if (
                    self.config.enable_season_matching
                    and parsed.season is None
                    and parsed.crop_category != "commercial_and_horticultural"
                ):
                    missing_context.append("season")
            elif parsed.rule_parameter == "central_subsidy_actuarial_cap":
                if self.config.enable_crop_category_matching and parsed.crop_category is None:
                    missing_context.append("crop_category")
            elif parsed.rule_parameter == "central_subsidy_share":
                if parsed.geography is None:
                    missing_context.append("geography")

            if missing_context:
                v_str, abs_reason = self._finalize_verdict(
                    Verdict.UNVERIFIABLE,
                    f"missing_required_claim_conditions({','.join(missing_context)})",
                    supporting_ids,
                    contradicting_ids,
                    valid_units,
                )
                return VerificationPrediction(
                    claim_id=claim_id,
                    predicted_verdict=v_str,
                    parsed_claim=parsed.to_dict(),
                    matched_evidence_ids=[u.evidence_id for u in valid_units],
                    supporting_evidence_ids=supporting_ids,
                    contradicting_evidence_ids=contradicting_ids,
                    context_mismatch=[],
                    temporal_status="ambiguous_claim_context",
                    verification_rationale=(
                        f"Claim omits required contextual condition(s) {missing_context}; "
                        f"FieldGuard preserves uncertainty rather than inventing missing conditions."
                    ),
                    abstention_reason=abs_reason,
                    retrieval_method=ret_method,
                    latency_ms=0.0,
                )

        # Check empty retrieval or invalid evidence IDs
        if not valid_units:
            reason = "invalid_evidence_ids_rejected" if invalid_ev_ids else "no_retrieved_evidence"
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                reason,
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=contradicting_ids,
                context_mismatch=[],
                temporal_status="no_valid_evidence_retrieved",
                verification_rationale=(
                    f"No valid evidence units available in retrieval ranking (reason={reason}). "
                    f"Absence of retrieved evidence is treated as UNVERIFIABLE, never CONTRADICTED."
                ),
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check if any retrieved unit has corrupted extraction quality when provenance validation is on
        valid_clean_units: list[ExtractedEvidenceUnit] = []
        corrupted_ev_ids: list[str] = []
        for u in valid_units:
            if self.config.enable_provenance_validation and u.extraction_quality != "high_verified":
                corrupted_ev_ids.append(u.evidence_id)
            else:
                valid_clean_units.append(u)

        if not valid_clean_units and corrupted_ev_ids:
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                "corrupted_evidence_extraction_quality",
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=contradicting_ids,
                context_mismatch=[],
                temporal_status="corrupted_evidence_rejected",
                verification_rationale=(
                    f"Retrieved evidence {corrupted_ev_ids} flagged with corrupted extraction quality; "
                    f"rejected by provenance validation."
                ),
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Build ConditionMatchConfig from VerifierConfig
        cm_config = ConditionMatchConfig(
            enable_structured_condition_matching=self.config.enable_structured_condition_matching,
            enable_crop_category_matching=self.config.enable_crop_category_matching,
            enable_season_matching=self.config.enable_season_matching,
            enable_qualification_matching=self.config.enable_qualification_matching,
            enable_temporal_checks=self.config.enable_temporal_checks,
            enable_provenance_validation=self.config.enable_provenance_validation,
        )

        # Gather all structured rules linked to the retrieved evidence units
        rule_evaluations: list[RuleMatchResult] = []
        unstructured_distractor_matches: list[dict[str, Any]] = []
        untrusted_source_matches: list[dict[str, Any]] = []

        seen_rule_ids: set[str] = set()
        for unit in valid_clean_units:
            linked_rules = self.store.get_rules_for_evidence(unit.evidence_id)
            if linked_rules:
                for r in linked_rules:
                    if r.rule_id in seen_rule_ids:
                        continue
                    seen_rule_ids.add(r.rule_id)
                    ev_res = evaluate_rule_against_claim(parsed, r, cm_config)
                    rule_evaluations.append(ev_res)
            else:
                chunk_check = check_unstructured_chunk_numeric_distractor(parsed, unit, cm_config)
                if chunk_check.get("has_number"):
                    if chunk_check.get("match_type") == "untrusted_source_number_match":
                        untrusted_source_matches.append(chunk_check)
                    elif chunk_check.get("match_type") == "unrelated_paragraph_distractor_number":
                        unstructured_distractor_matches.append(chunk_check)

        # Check if official conflicting rules match the requested context
        conflicting_context_evals = [
            ev for ev in rule_evaluations if ev.provenance_valid and ev.context_matches_all and ev.conflict_flag
        ]
        if conflicting_context_evals:
            conflict_ev_ids = sorted({ev.evidence_id for ev in conflicting_context_evals})
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                "conflicting_official_sources",
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=conflict_ev_ids,
                context_mismatch=[],
                temporal_status=conflicting_context_evals[0].temporal_result.temporal_status,
                verification_rationale=(
                    f"Conflicting official sources detected in {conflict_ev_ids} for context "
                    f"(season={parsed.season}, crop={parsed.crop_category}). "
                    f"FieldGuard preserves both records and abstains (UNVERIFIABLE) rather than silently selecting one."
                ),
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check for full support among evaluated structured rules
        full_supports = [ev for ev in rule_evaluations if ev.is_full_support]
        if full_supports:
            supporting_ids = sorted({ev.evidence_id for ev in full_supports})
            best = full_supports[0]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.SUPPORTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=[],
                context_mismatch=[],
                temporal_status=best.temporal_result.temporal_status,
                verification_rationale=(
                    f"Claim is SUPPORTED by verified rule {best.rule_id} in {best.evidence_id} "
                    f"(document={best.source_document_id}, temporal_status={best.temporal_result.temporal_status})."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check if an untrusted source matched when provenance validation is disabled (Ablation 7)
        if untrusted_source_matches and not self.config.enable_provenance_validation:
            u_ev_id = untrusted_source_matches[0]["evidence_id"]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.SUPPORTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[u_ev_id],
                contradicting_evidence_ids=[],
                context_mismatch=[],
                temporal_status="provenance_validation_disabled",
                verification_rationale=(
                    f"Provenance validation disabled (Ablation): accepted untrusted source {u_ev_id}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check if an unrelated distractor paragraph matched when structured condition matching is disabled (Ablation 2)
        if unstructured_distractor_matches and not self.config.enable_structured_condition_matching:
            d_ev_id = unstructured_distractor_matches[0]["evidence_id"]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.SUPPORTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[d_ev_id],
                contradicting_evidence_ids=[],
                context_mismatch=[],
                temporal_status="condition_matching_disabled",
                verification_rationale=(
                    f"Structured condition matching disabled (Ablation): accepted distractor number in {d_ev_id}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check explicit request for unverified latest/current or post-Dec-2025 full revised policy
        if self.config.enable_temporal_checks and parsed.requested_policy_version in (
            "latest_current",
            "2026_revised_full_unverified",
            "2025_dec_full_guidelines_unverified",
        ):
            t_status = "unresolved_latest_policy_version"
            t_expl = "Requested latest/post-Dec-2025 full policy version cannot be established from historical 2023 guidelines."
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                t_status,
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=contradicting_ids,
                context_mismatch=[],
                temporal_status=t_status,
                verification_rationale=f"Temporal resolution requires abstention (UNVERIFIABLE): {t_expl}",
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        wrong_context_evals = [ev for ev in rule_evaluations if ev.is_wrong_context_for_matched_number]
        same_context_contradictions = [ev for ev in rule_evaluations if ev.is_contradiction_in_same_context]
        same_context_qual_or_basis_contradictions = [
            ev for ev in same_context_contradictions if ev.value_unit_match
        ]

        # If the retrieved rule for the EXACT requested context matches the claimed number & unit
        # but contradicts its mandatory qualification, basis/denominator, or comparison operator,
        # it is a direct same-context contradiction (CONTRADICTED).
        if same_context_qual_or_basis_contradictions:
            contra_ids = sorted({ev.evidence_id for ev in same_context_qual_or_basis_contradictions})
            c0 = same_context_qual_or_basis_contradictions[0]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.CONTRADICTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=contra_ids,
                context_mismatch=[],
                temporal_status=c0.temporal_result.temporal_status,
                verification_rationale=(
                    f"Claim is CONTRADICTED in the requested context by rule {c0.rule_id} in {c0.evidence_id}: "
                    f"{c0.mismatch_reasons}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check for WRONG_CONTEXT:
        # Claimed number does not match the requested context, but matches a rule in a DIFFERENT context
        # (different crop_category, season, geography, or superseded policy version) or a distractor paragraph.
        if wrong_context_evals:
            for wc in wrong_context_evals:
                context_mismatches.extend(wc.context_mismatch_dimensions)
            context_mismatches = list(dict.fromkeys(context_mismatches))
            contra_ev_ids = sorted(
                {ev.evidence_id for ev in wrong_context_evals + same_context_contradictions}
            )
            wc0 = wrong_context_evals[0]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.WRONG_CONTEXT.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=contra_ev_ids,
                context_mismatch=context_mismatches,
                temporal_status=wc0.temporal_result.temporal_status,
                verification_rationale=(
                    f"Claimed value ({parsed.claimed_value} {parsed.claimed_unit}) belongs to a different context "
                    f"in rule {wc0.rule_id} ({wc0.evidence_id}): {context_mismatches}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        if unstructured_distractor_matches:
            d_match = unstructured_distractor_matches[0]
            context_mismatches = ["unrelated_paragraph_distractor_number"]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.WRONG_CONTEXT.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[d_match["evidence_id"]],
                context_mismatch=context_mismatches,
                temporal_status="distractor_context_mismatch",
                verification_rationale=(
                    f"Claimed number ({d_match['raw_mention']}) appears in unrelated administrative/outreach paragraph "
                    f"{d_match['evidence_id']} rather than an applicable policy rule for {parsed.rule_parameter}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check for CONTRADICTED value in the same requested context
        if same_context_contradictions:
            contra_ids = sorted({ev.evidence_id for ev in same_context_contradictions})
            c0 = same_context_contradictions[0]
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=Verdict.CONTRADICTED.value,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=[],
                contradicting_evidence_ids=contra_ids,
                context_mismatch=[],
                temporal_status=c0.temporal_result.temporal_status,
                verification_rationale=(
                    f"Claim is CONTRADICTED by applicable rule {c0.rule_id} in {c0.evidence_id}: "
                    f"{c0.mismatch_reasons}."
                ),
                abstention_reason=None,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check for temporal abstention when the only matching rules require temporal abstention
        # (e.g., asking for an effective date of the Dec 2025 PIB announcement, or having only undated FAQ evidence
        # for a dated guideline query)
        temporal_abstentions = [
            ev
            for ev in rule_evaluations
            if ev.provenance_valid
            and ev.scheme_match
            and ev.parameter_match
            and ev.crop_category_match
            and ev.season_match
            and ev.geography_match
            and ev.temporal_result.requires_abstention
        ]
        if temporal_abstentions:
            t_status = temporal_abstentions[0].temporal_result.temporal_status
            t_expl = temporal_abstentions[0].temporal_result.explanation
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                t_status,
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=contradicting_ids,
                context_mismatch=[],
                temporal_status=t_status,
                verification_rationale=f"Temporal resolution requires abstention (UNVERIFIABLE): {t_expl}",
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Check if only untrusted sources matched the number (and provenance validation rejected them)
        if untrusted_source_matches:
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                "unverified_source_provenance_rejected",
                supporting_ids,
                contradicting_ids,
                valid_units,
            )
            return VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=v_str,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=[u.evidence_id for u in valid_units],
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=contradicting_ids,
                context_mismatch=[],
                temporal_status="untrusted_source_rejected",
                verification_rationale=(
                    f"Evidence {untrusted_source_matches[0]['evidence_id']} comes from an unverified source "
                    f"({untrusted_source_matches[0]['document_id']}) and cannot establish support."
                ),
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Otherwise: Retrieved evidence does not contain applicable rules for the requested context
        # (e.g. non-covered crop/scheme, relevant evidence omitted from top-k retrieval, or lexically similar irrelevant chunks).
        # Absence of applicable evidence is UNVERIFIABLE, never CONTRADICTED!
        v_str, abs_reason = self._finalize_verdict(
            Verdict.UNVERIFIABLE,
            "insufficient_or_missing_applicable_evidence",
            supporting_ids,
            contradicting_ids,
            valid_units,
        )
        return VerificationPrediction(
            claim_id=claim_id,
            predicted_verdict=v_str,
            parsed_claim=parsed.to_dict(),
            matched_evidence_ids=[u.evidence_id for u in valid_units],
            supporting_evidence_ids=supporting_ids,
            contradicting_evidence_ids=contradicting_ids,
            context_mismatch=[],
            temporal_status="no_applicable_rule_in_retrieved_evidence",
            verification_rationale=(
                "Retrieved evidence does not contain an applicable verified rule for the requested "
                f"scheme ({parsed.scheme}), parameter ({parsed.rule_parameter}), season ({parsed.season}), "
                f"and crop category ({parsed.crop_category}). Abstaining with UNVERIFIABLE."
            ),
            abstention_reason=abs_reason,
            retrieval_method=ret_method,
            latency_ms=0.0,
        )
