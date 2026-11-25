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
from fieldguard.schemes import get_scheme_adapter
from fieldguard.verdicts import Verdict
from fieldguard.uploaded_verification import compare_uploaded_claim, evaluate_uploaded_claim, is_uploaded
from fieldguard.compound_claims import pm_kisan_components


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
    retrieval_only_min_score: float = 0.01


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
    verification_scope: str = "official_policy"
    component_results: list[dict[str, Any]] = field(default_factory=list)
    matched_passage: str | None = None
    matched_candidate_rule: dict[str, Any] | None = None
    matched_page: int | None = None
    matched_score: float | None = None
    verdict_reason_code: str | None = None

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

        # Step 1: Parse the question and candidate claim (inferring default_scheme if store is single-scheme)
        known_schemes = {r.scheme for r in self.store.trusted_rules.values() if r.scheme}
        default_scheme = next(iter(known_schemes)) if len(known_schemes) == 1 else None
        if pre_parsed_claim is not None:
            parsed = pre_parsed_claim
        else:
            try:
                parsed = self.parser.parse(
                    question=question,
                    candidate_claim=candidate_claim,
                    default_scheme=default_scheme,
                )
            except TypeError:
                parsed = self.parser.parse(question=question, candidate_claim=candidate_claim)

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
        if any(is_uploaded(u) for u in valid_units) or (
            self.store.evidence_units
            and all(is_uploaded(u) for u in self.store.evidence_units.values())
        ):
            # Uploads never enter official-policy verification or permissive ablations.
            upload_eval = evaluate_uploaded_claim(
                candidate_claim, valid_units, list(self.store.evidence_units.values())
            )
            verdict = upload_eval["verdict"]
            support = upload_eval["supporting_ids"]
            contra = upload_eval["contradicting_ids"]
            reason = upload_eval["reason"]
            reason_code = upload_eval.get("reason_code")
            pred = VerificationPrediction(
                claim_id=claim_id,
                predicted_verdict=verdict,
                parsed_claim=parsed.to_dict(),
                matched_evidence_ids=matched_ev_ids,
                supporting_evidence_ids=support,
                contradicting_evidence_ids=contra,
                context_mismatch=upload_eval.get("context_mismatch", []),
                temporal_status="uploaded_policy_applicability_unverified",
                verification_rationale=(reason + " Comparison is limited to the uploaded document; "
                                        "official provenance and current policy applicability are unverified."),
                abstention_reason=(reason_code or "uploaded_conditions_not_established") if verdict == "UNVERIFIABLE" else None,
                retrieval_method=ret_method,
                latency_ms=0.0,
                verification_scope="uploaded_document_only",
                matched_passage=upload_eval.get("matched_passage"),
                matched_candidate_rule=upload_eval.get("matched_candidate_rule"),
                matched_page=upload_eval.get("matched_page"),
                matched_score=upload_eval.get("matched_score"),
                verdict_reason_code=reason_code,
            )
        elif self.config.mode == "retrieval_only":
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
            components = pm_kisan_components(parsed) if self.config.mode == "fieldguard" else []
            predictions = [self._run_fieldguard_pipeline(
                claim_id=claim_id, parsed=part, valid_units=valid_units,
                invalid_ev_ids=invalid_ev_ids, ret_method=ret_method,
            ) for part in (components or [parsed])]
            pred = predictions[0]
            if components:
                # A conjunction is supported only when every numerical component is supported.
                priority = {"CONTRADICTED": 0, "WRONG_CONTEXT": 1, "UNVERIFIABLE": 2, "SUPPORTED": 3}
                pred = min(predictions, key=lambda item: priority[item.predicted_verdict])
                details = [{"parameter": part.rule_parameter, "value": part.claimed_value,
                            "unit": part.claimed_unit, "verdict": result.predicted_verdict,
                            "rationale": result.verification_rationale}
                           for part, result in zip(components, predictions)]
                pred.component_results = details
                pred.parsed_claim = parsed.to_dict()
                pred.supporting_evidence_ids = sorted({eid for result in predictions for eid in result.supporting_evidence_ids})
                pred.contradicting_evidence_ids = sorted({eid for result in predictions for eid in result.contradicting_evidence_ids})
                pred.verification_rationale = "Checked each numerical component: " + "; ".join(
                    f"{row['parameter'] or 'unresolved number'}={row['value']} {row['unit']}: {row['verdict']}" for row in details)

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

    def _infer_parameter_from_retrieval(
        self,
        parsed: ParsedClaim,
        valid_units: list[ExtractedEvidenceUnit],
    ) -> None:
        """
        Retrieval-guided fallback for inferring `rule_parameter` when the deterministic parser
        could not pick a parameter from keywords alone. Compares the claimed number, unit, and
        topic keywords against candidate rules in top-k retrieved passages and scheme store.
        """
        if parsed.claimed_value is None or parsed.claimed_unit is None:
            return
        if parsed.scheme == "PM_KISAN":
            return

        known_params_for_scheme = {
            r.rule_parameter
            for r in self.store.trusted_rules.values()
            if parsed.scheme is None or r.scheme == parsed.scheme
        }
        if parsed.rule_parameter is not None and parsed.rule_parameter in known_params_for_scheme:
            return

        candidate_rules = []
        seen_ids: set[str] = set()
        for u in valid_units:
            for r in self.store.get_rules_for_evidence(u.evidence_id):
                if r.rule_id not in seen_ids and (parsed.scheme is None or r.scheme == parsed.scheme):
                    seen_ids.add(r.rule_id)
                    candidate_rules.append((r, u.text, True))
        for r in self.store.trusted_rules.values():
            if r.rule_id not in seen_ids and (parsed.scheme is None or r.scheme == parsed.scheme):
                seen_ids.add(r.rule_id)
                u_obj = self.store.get_evidence_unit(r.evidence_id)
                candidate_rules.append((r, u_obj.text if u_obj else "", False))

        if not candidate_rules:
            return

        stopwords = {
            "under", "scheme", "yojana", "pradhan", "mantri", "mahatma", "gandhi",
            "guidelines", "operational", "act", "percent", "percentage", "rupees",
            "inr", "rs", "lakh", "lakhs", "crore", "days", "years", "months", "hours",
            "eligible", "farmers", "farmer", "households", "household", "family",
            "families", "beneficiaries", "beneficiary", "provided", "receive",
            "received", "entitled", "maximum", "minimum", "upto", "mgnrega", "mgnregs",
            "nrega", "pmjay", "ayushman", "bharat", "pmay", "gramin", "kusum", "pmmy",
            "mudra", "pmfby", "kisan", "samman", "nidhi", "what", "much", "many",
            "is", "the", "of", "in", "for", "to", "and", "or", "per", "from", "with",
            "are", "can", "be", "at", "by", "that", "this", "an", "as", "on", "all",
            "total", "amount", "rate", "limit", "cap", "number", "value", "financial",
            "assistance", "support", "benefit", "government", "india", "national",
            "subsidy", "grant", "allowance", "registered", "workers", "completion",
            "price", "guaranteed", "season", "annual", "monthly", "norm", "statutory",
            "provision", "guideline", "official", "rule",
        }
        claim_text = f"{parsed.raw_question} {parsed.raw_claim}".lower()
        claim_tokens = {
            tok for tok in re.findall(r"[a-z]{3,}", claim_text) if tok not in stopwords
        }
        if not claim_tokens:
            return

        adapter = get_scheme_adapter(parsed.scheme) if parsed.scheme else None
        param_desc_map: dict[str, str] = {}
        if adapter and hasattr(adapter, "parameters"):
            for p in adapter.parameters:
                if hasattr(p, "name") and hasattr(p, "description"):
                    param_desc_map[p.name] = p.description.lower()

        best_param: str | None = None
        best_score = 0.0

        for r, u_text, in_top_k in candidate_rules:
            val_ok, msg = compare_numeric_values(
                parsed.claimed_value,
                parsed.claimed_unit,
                r.maximum_rate,
                r.unit,
                allowed_values=r.allowed_values,
            )
            if "unit mismatch" in msg.lower():
                continue

            param_text = " ".join(
                [
                    r.rule_parameter.replace("_", " "),
                    (r.basis or "").replace("_", " "),
                    (r.qualifier or "").replace("_", " "),
                    param_desc_map.get(r.rule_parameter, ""),
                ]
            ).lower()
            param_tokens = {
                tok for tok in re.findall(r"[a-z]{3,}", param_text) if tok not in stopwords
            }
            unit_tokens = {
                tok for tok in re.findall(r"[a-z]{3,}", u_text.lower()) if tok not in stopwords
            }
            param_overlap = len(claim_tokens & param_tokens)
            passage_overlap = len(claim_tokens & unit_tokens)
            if param_overlap == 0:
                continue

            score = (param_overlap * 3.0) + (passage_overlap * 1.0)
            if in_top_k:
                score += 1.5
            if val_ok:
                score += 2.0

            if score > best_score:
                best_score = score
                best_param = r.rule_parameter

        if best_param is not None and best_score >= 3.0:
            parsed.rule_parameter = best_param
            if "rule_parameter" in parsed.uncertain_fields:
                parsed.uncertain_fields.remove("rule_parameter")
            if not parsed.uncertain_fields and parsed.parse_status == "partial_uncertain":
                parsed.parse_status = "success"

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
                "parser_failed",
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
                    "Claim parsing failed or numeric value/unit is corrupted/missing (parser_failed); "
                    "malformed claims cannot bypass verification."
                ),
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        # Infer scheme from evidence store or retrieved units when omitted in claim
        if parsed.scheme is None:
            known_schemes = {r.scheme for r in self.store.trusted_rules.values() if r.scheme}
            if len(known_schemes) == 1:
                parsed.scheme = next(iter(known_schemes))
            else:
                ret_schemes = {
                    r.scheme
                    for u in valid_units
                    for r in self.store.get_rules_for_evidence(u.evidence_id)
                    if r.scheme
                }
                if len(ret_schemes) == 1:
                    parsed.scheme = next(iter(ret_schemes))

        # Fall back to retrieval-guided parameter inference if parser could not pick a parameter
        self._infer_parameter_from_retrieval(parsed, valid_units)

        # Check if required contextual fields are uncertain/unspecified when condition matching is enabled
        if self.config.enable_structured_condition_matching:
            missing_context: list[str] = []
            if parsed.scheme is None:
                missing_context.append("scheme")

            if parsed.scheme is not None:
                scheme_adapter = get_scheme_adapter(parsed.scheme)
                if scheme_adapter:
                    ctx_dict = {
                        "crop_category": parsed.crop_category,
                        "season": parsed.season,
                        "geography": parsed.geography,
                        "beneficiary_type": getattr(parsed, "beneficiary_type", None) or parsed.crop_category,
                        "entity_scope": getattr(parsed, "entity_scope", None) or parsed.crop_category,
                        "exclusion_category": getattr(parsed, "exclusion_category", None),
                        "frequency": getattr(parsed, "frequency", None),
                    }
                    val_res = scheme_adapter.validate_claim_context(
                        parsed.rule_parameter,
                        ctx_dict,
                        enable_switches={
                            "enable_crop_category_matching": self.config.enable_crop_category_matching,
                            "enable_season_matching": self.config.enable_season_matching,
                        },
                    )
                    if not val_res.is_valid:
                        missing_context.extend(val_res.missing_fields)
                    if parsed.rule_parameter is None and "rule_parameter" not in missing_context:
                        missing_context.append("rule_parameter")
                else:
                    if parsed.rule_parameter is None:
                        missing_context.append("rule_parameter")

            if missing_context:
                diag_reason = (
                    "no_rule_for_parameter"
                    if missing_context == ["rule_parameter"]
                    else f"missing_required_claim_conditions({','.join(missing_context)})"
                )
                v_str, abs_reason = self._finalize_verdict(
                    Verdict.UNVERIFIABLE,
                    diag_reason,
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
                        f"Claim cannot be verified (reason={diag_reason}, missing={missing_context}); "
                        f"FieldGuard preserves uncertainty rather than inventing missing conditions or rules."
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
            "2028_unverified_draft",
        ):
            t_status = "unresolved_latest_policy_version"
            t_expl = "Requested latest/post-Dec-2025 full policy version cannot be established from historical 2023 guidelines."
            v_str, abs_reason = self._finalize_verdict(
                Verdict.UNVERIFIABLE,
                "temporal_ambiguity",
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
                verification_rationale=f"Temporal resolution requires abstention (UNVERIFIABLE, reason=temporal_ambiguity): {t_expl}",
                abstention_reason=abs_reason,
                retrieval_method=ret_method,
                latency_ms=0.0,
            )

        wrong_context_evals = [ev for ev in rule_evaluations if ev.is_wrong_context_for_matched_number]
        same_context_contradictions = [ev for ev in rule_evaluations if ev.is_contradiction_in_same_context]
        same_context_qual_or_basis_contradictions = [
            ev for ev in same_context_contradictions if ev.value_unit_match
        ]
        direct_eligibility_exclusion_contradictions = [
            ev
            for ev in same_context_contradictions
            if (
                ev.rule_id.startswith("RULE_PMKISAN_EXCL_")
                or ev.rule_id in ("RULE_PMKISAN_TENANT_INELIGIBLE", "RULE_PMKISAN_LABORER_INELIGIBLE")
            )
            and bool(re.search(r"\beligible\b", parsed.raw_claim or "", re.I))
        ]

        # If the retrieved rule for the EXACT requested context matches the claimed number & unit
        # but contradicts its mandatory qualification, basis/denominator, or comparison operator,
        # it is a direct same-context contradiction (CONTRADICTED).
        if same_context_qual_or_basis_contradictions or direct_eligibility_exclusion_contradictions:
            target_contras = (
                same_context_qual_or_basis_contradictions or direct_eligibility_exclusion_contradictions
            )
            contra_ids = sorted({ev.evidence_id for ev in target_contras})
            c0 = target_contras[0]
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
                "temporal_ambiguity",
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
                verification_rationale=f"Temporal resolution requires abstention (UNVERIFIABLE, reason=temporal_ambiguity): {t_expl}",
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
            "no_rule_for_parameter",
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
                "Retrieved evidence does not contain an applicable verified rule (reason=no_rule_for_parameter) "
                f"for the requested scheme ({parsed.scheme}), parameter ({parsed.rule_parameter}), "
                f"season ({parsed.season}), and crop category ({parsed.crop_category}). Abstaining with UNVERIFIABLE."
            ),
            abstention_reason=abs_reason,
            retrieval_method=ret_method,
            latency_ms=0.0,
        )
