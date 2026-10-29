"""Evidence-grounded error analysis across baselines and Full FieldGuard (Phase 12 & 14)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fieldguard.benchmark_builder import BenchmarkClaimRecord
from fieldguard.verdicts import Verdict


def generate_error_analysis_report(
    claims: list[BenchmarkClaimRecord],
    predictions_by_method: dict[str, list[dict[str, Any]]],
    output_doc_path: Path,
) -> dict[str, Any]:
    """
    Analyze actual predictions across methods, categorizing:
      1. False-support cases in simpler baselines (Baseline A, Baseline B, Baseline C) corrected by FieldGuard.
      2. Wrong-context failures (5% commercial rate on Kharif food grains, 2% Kharif on Rabi, distractor numbers).
      3. Qualification and denominator failures ('always pays flat 2%', '2% of Threshold Yield').
      4. Temporal grounding failures (2016 historical rules applied to 2023 guidelines, unverified 2026 queries).
      5. Retrieval misses and cases where FieldGuard abstained correctly (`UNVERIFIABLE`).
      6. Any residual errors in FieldGuard.
    """
    claim_map = {c.claim_id: c for c in claims}

    fg_preds = predictions_by_method.get("fieldguard_full", [])
    b_num_preds = predictions_by_method.get("baseline_b_numeric_only", [])
    b_ctx_preds = predictions_by_method.get("baseline_c_numeric_basic_context", [])
    b_ret_preds = predictions_by_method.get("baseline_a_retrieval_only", [])

    fg_by_id = {p["claim_id"]: p for p in fg_preds}
    b_num_by_id = {p["claim_id"]: p for p in b_num_preds}
    b_ctx_by_id = {p["claim_id"]: p for p in b_ctx_preds}
    b_ret_by_id = {p["claim_id"]: p for p in b_ret_preds}

    wrong_context_caught: list[dict[str, Any]] = []
    qualification_caught: list[dict[str, Any]] = []
    temporal_caught: list[dict[str, Any]] = []
    correct_abstentions: list[dict[str, Any]] = []
    fg_residual_errors: list[dict[str, Any]] = []

    for clm in claims:
        cid = clm.claim_id
        fg_p = fg_by_id.get(cid, {})
        bn_p = b_num_by_id.get(cid, {})
        bc_p = b_ctx_by_id.get(cid, {})

        if fg_p.get("predicted_verdict") != clm.gold_verdict:
            fg_residual_errors.append(
                {
                    "claim_id": cid,
                    "claim_type": clm.claim_type,
                    "question": clm.question,
                    "candidate_claim": clm.candidate_claim,
                    "gold_verdict": clm.gold_verdict,
                    "predicted_verdict": fg_p.get("predicted_verdict"),
                    "matched_evidence_ids": fg_p.get("matched_evidence_ids", []),
                    "rationale": fg_p.get("verification_rationale", ""),
                }
            )

        if (
            clm.gold_verdict == Verdict.WRONG_CONTEXT.value
            and bn_p.get("predicted_verdict") == Verdict.SUPPORTED.value
            and fg_p.get("predicted_verdict") == Verdict.WRONG_CONTEXT.value
        ):
            wrong_context_caught.append(
                {
                    "claim_id": cid,
                    "claim_type": clm.claim_type,
                    "question": clm.question,
                    "candidate_claim": clm.candidate_claim,
                    "baseline_b_verdict": bn_p.get("predicted_verdict"),
                    "fieldguard_verdict": fg_p.get("predicted_verdict"),
                    "context_mismatch": fg_p.get("context_mismatch", []),
                    "rationale": fg_p.get("verification_rationale", ""),
                }
            )

        if (
            clm.claim_type in ("cat05_qualification_violation", "cat12_wrong_unit_denominator_operator")
            and bc_p.get("predicted_verdict") == Verdict.SUPPORTED.value
            and fg_p.get("predicted_verdict") == Verdict.CONTRADICTED.value
        ):
            qualification_caught.append(
                {
                    "claim_id": cid,
                    "claim_type": clm.claim_type,
                    "question": clm.question,
                    "candidate_claim": clm.candidate_claim,
                    "baseline_c_verdict": bc_p.get("predicted_verdict"),
                    "fieldguard_verdict": fg_p.get("predicted_verdict"),
                    "rationale": fg_p.get("verification_rationale", ""),
                }
            )

        if (
            clm.claim_type in ("cat07_inappropriate_historical_version", "cat08_unresolved_effective_date_or_current")
            and bc_p.get("predicted_verdict") == Verdict.SUPPORTED.value
            and fg_p.get("predicted_verdict") == clm.gold_verdict
        ):
            temporal_caught.append(
                {
                    "claim_id": cid,
                    "claim_type": clm.claim_type,
                    "question": clm.question,
                    "candidate_claim": clm.candidate_claim,
                    "baseline_c_verdict": bc_p.get("predicted_verdict"),
                    "fieldguard_verdict": fg_p.get("predicted_verdict"),
                    "temporal_status": fg_p.get("temporal_status", ""),
                    "rationale": fg_p.get("verification_rationale", ""),
                }
            )

        if (
            clm.gold_verdict == Verdict.UNVERIFIABLE.value
            and fg_p.get("predicted_verdict") == Verdict.UNVERIFIABLE.value
        ):
            correct_abstentions.append(
                {
                    "claim_id": cid,
                    "claim_type": clm.claim_type,
                    "question": clm.question,
                    "candidate_claim": clm.candidate_claim,
                    "abstention_reason": fg_p.get("abstention_reason"),
                    "rationale": fg_p.get("verification_rationale", ""),
                }
            )

    lines = [
        "# FieldGuard — Evidence-Grounded Error Analysis (Phase 14)",
        "",
        "## 1. Overview of Error Taxonomy",
        "",
        f"- **Evaluated Split Size:** {len(claims)} benchmark claims.",
        f"- **Wrong-Context False Supports in Baseline B (`numeric_only`) Caught by FieldGuard:** {len(wrong_context_caught)} cases.",
        f"- **Qualification & Denominator False Supports in Baseline C (`numeric_basic_context`) Caught by FieldGuard:** {len(qualification_caught)} cases.",
        f"- **Temporal / Policy-Version False Supports in Baseline C Caught by FieldGuard:** {len(temporal_caught)} cases.",
        f"- **Correct Abstentions (`UNVERIFIABLE`) by FieldGuard:** {len(correct_abstentions)} cases.",
        f"- **Residual Verdict Errors in Full FieldGuard:** {len(fg_residual_errors)} cases.",
        "",
        "## 2. Representative Wrong-Context Failures in Baselines (Corrected by FieldGuard)",
        "",
    ]

    for ex in wrong_context_caught[:5]:
        lines.extend(
            [
                f"### Case `{ex['claim_id']}` (`{ex['claim_type']}`)",
                f"- **Question:** {ex['question']}",
                f"- **Candidate Claim:** {ex['candidate_claim']}",
                f"- **Numeric-Only Baseline Verdict:** `{ex['baseline_b_verdict']}` (False Support)",
                f"- **FieldGuard Verdict:** `{ex['fieldguard_verdict']}`",
                f"- **Detected Context Mismatch:** `{ex['context_mismatch']}`",
                f"- **FieldGuard Rationale:** {ex['rationale']}",
                "",
            ]
        )

    lines.extend(
        [
            "## 3. Representative Qualification & Denominator Failures in Basic-Context Baseline",
            "",
        ]
    )
    for ex in qualification_caught[:4]:
        lines.extend(
            [
                f"### Case `{ex['claim_id']}` (`{ex['claim_type']}`)",
                f"- **Question:** {ex['question']}",
                f"- **Candidate Claim:** {ex['candidate_claim']}",
                f"- **Basic-Context Baseline Verdict:** `{ex['baseline_c_verdict']}` (False Support)",
                f"- **FieldGuard Verdict:** `{ex['fieldguard_verdict']}`",
                f"- **FieldGuard Rationale:** {ex['rationale']}",
                "",
            ]
        )

    lines.extend(
        [
            "## 4. Representative Temporal & Policy-Version Failures in Basic-Context Baseline",
            "",
        ]
    )
    for ex in temporal_caught[:4]:
        lines.extend(
            [
                f"### Case `{ex['claim_id']}` (`{ex['claim_type']}`)",
                f"- **Question:** {ex['question']}",
                f"- **Candidate Claim:** {ex['candidate_claim']}",
                f"- **Basic-Context Baseline Verdict:** `{ex['baseline_c_verdict']}` (False Support)",
                f"- **FieldGuard Verdict:** `{ex['fieldguard_verdict']}` (`temporal_status={ex['temporal_status']}`)",
                f"- **FieldGuard Rationale:** {ex['rationale']}",
                "",
            ]
        )

    lines.extend(
        [
            "## 5. Representative Correct Abstentions (`UNVERIFIABLE`: Missing Evidence, Conflicts, Retrieval Misses)",
            "",
        ]
    )
    for ex in correct_abstentions[:5]:
        lines.extend(
            [
                f"### Case `{ex['claim_id']}` (`{ex['claim_type']}`)",
                f"- **Question:** {ex['question']}",
                f"- **Candidate Claim:** {ex['candidate_claim']}",
                f"- **Abstention Reason:** `{ex['abstention_reason']}`",
                f"- **FieldGuard Rationale:** {ex['rationale']}",
                "",
            ]
        )

    lines.extend(
        [
            "## 6. Residual Failure Modes and Boundary Analysis",
            "",
        ]
    )
    if fg_residual_errors:
        for ex in fg_residual_errors[:5]:
            lines.extend(
                [
                    f"### Residual Error `{ex['claim_id']}` (`{ex['claim_type']}`)",
                    f"- **Gold Verdict:** `{ex['gold_verdict']}` | **Predicted:** `{ex['predicted_verdict']}`",
                    f"- **Rationale:** {ex['rationale']}",
                    "",
                ]
            )
    else:
        lines.append(
            "On the canonical PMFBY benchmark split, Full FieldGuard achieved zero false-support errors when gold evidence was present in top-$k$ retrieval; when gold evidence was omitted in controlled retrieval-miss cases (`cat14_omitted_retrieval_evidence`), FieldGuard abstained safely (`UNVERIFIABLE`) rather than hallucinating support or contradiction."
        )

    output_doc_path.parent.mkdir(parents=True, exist_ok=True)
    output_doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "wrong_context_caught_count": len(wrong_context_caught),
        "qualification_caught_count": len(qualification_caught),
        "temporal_caught_count": len(temporal_caught),
        "correct_abstentions_count": len(correct_abstentions),
        "fg_residual_errors_count": len(fg_residual_errors),
    }
