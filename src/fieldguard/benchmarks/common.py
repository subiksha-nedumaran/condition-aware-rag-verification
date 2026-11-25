"""Shared benchmark construction, family-split validation, and JSONL persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fieldguard.benchmark_builder import BenchmarkClaimRecord
from fieldguard.verdicts import Verdict


@dataclass(frozen=True)
class ClaimFamilySpec:
    """Compact specification of a 4-variant claim family (SUPPORTED, CONTRADICTED, WRONG_CONTEXT, UNVERIFIABLE)."""

    family_id: str
    split: str  # 'train', 'dev', 'test'
    rule_parameter: str
    evidence_ids: list[str]
    sup_question: str
    sup_claim: str
    sup_value: float
    sup_unit: str
    sup_operator: str
    crop_category: str | None
    season: str | None
    geography: str | None
    con_claim: str
    con_value: float
    con_operator: str
    wc_question: str
    wc_claim: str
    wc_value: float
    wc_unit: str
    wc_operator: str
    wc_crop_category: str | None
    wc_geography: str | None
    unv_question: str
    unv_claim: str
    unv_value: float
    unv_unit: str
    unv_policy_version: str | None = None
    sup_rationale: str = ""
    con_rationale: str = ""
    wc_rationale: str = ""
    unv_rationale: str = ""
    wc_rule_parameter: str | None = None
    unv_rule_parameter: str | None = None
    wc_evidence_ids: list[str] | None = None


def expand_family_specs(
    scheme: str,
    prefix: str,
    case_origin: str,
    specs: Iterable[ClaimFamilySpec],
) -> list[BenchmarkClaimRecord]:
    """Expand each ClaimFamilySpec into 4 gold-annotated BenchmarkClaimRecord variants."""
    records: list[BenchmarkClaimRecord] = []
    idx = 1
    for spec in specs:
        split_tag = spec.split.upper()
        # 1. SUPPORTED
        records.append(
            BenchmarkClaimRecord(
                claim_id=f"{prefix}_{split_tag}_{idx:03d}",
                question=spec.sup_question,
                candidate_claim=spec.sup_claim,
                claimed_value=spec.sup_value,
                claimed_unit=spec.sup_unit,
                numeric_operator=spec.sup_operator,
                scheme=scheme,
                crop_category=spec.crop_category,
                season=spec.season,
                geography=spec.geography,
                qualification=None,
                requested_policy_version=None,
                requested_effective_date=None,
                claim_type="numerical_factual",
                gold_verdict=Verdict.SUPPORTED.value,
                gold_evidence_ids=list(spec.evidence_ids),
                gold_rationale=spec.sup_rationale or f"Supported by {spec.evidence_ids[0]}.",
                case_origin=case_origin,
                annotation_status="gold_verified",
                annotator_notes=f"{scheme} benchmark family {spec.family_id}",
                claim_family_id=spec.family_id,
                split=spec.split,
                rule_parameter=spec.rule_parameter,
            )
        )
        idx += 1

        # 2. CONTRADICTED
        records.append(
            BenchmarkClaimRecord(
                claim_id=f"{prefix}_{split_tag}_{idx:03d}",
                question=spec.sup_question,
                candidate_claim=spec.con_claim,
                claimed_value=spec.con_value,
                claimed_unit=spec.sup_unit,
                numeric_operator=spec.con_operator,
                scheme=scheme,
                crop_category=spec.crop_category,
                season=spec.season,
                geography=spec.geography,
                qualification=None,
                requested_policy_version=None,
                requested_effective_date=None,
                claim_type="numerical_factual",
                gold_verdict=Verdict.CONTRADICTED.value,
                gold_evidence_ids=list(spec.evidence_ids),
                gold_rationale=spec.con_rationale or f"Contradicted by {spec.evidence_ids[0]}.",
                case_origin=case_origin,
                annotation_status="gold_verified",
                annotator_notes=f"{scheme} benchmark family {spec.family_id}",
                claim_family_id=spec.family_id,
                split=spec.split,
                rule_parameter=spec.rule_parameter,
            )
        )
        idx += 1

        # 3. WRONG_CONTEXT
        records.append(
            BenchmarkClaimRecord(
                claim_id=f"{prefix}_{split_tag}_{idx:03d}",
                question=spec.wc_question,
                candidate_claim=spec.wc_claim,
                claimed_value=spec.wc_value,
                claimed_unit=spec.wc_unit,
                numeric_operator=spec.wc_operator,
                scheme=scheme,
                crop_category=spec.wc_crop_category,
                season=spec.season,
                geography=spec.wc_geography,
                qualification=None,
                requested_policy_version=None,
                requested_effective_date=None,
                claim_type="context_perturbation",
                gold_verdict=Verdict.WRONG_CONTEXT.value,
                gold_evidence_ids=list(spec.wc_evidence_ids or spec.evidence_ids),
                gold_rationale=spec.wc_rationale or "Wrong context: official value applied to mismatched scope/category/geography.",
                case_origin=case_origin,
                annotation_status="gold_verified",
                annotator_notes=f"{scheme} benchmark family {spec.family_id}",
                claim_family_id=spec.family_id,
                split=spec.split,
                rule_parameter=spec.wc_rule_parameter or spec.rule_parameter,
            )
        )
        idx += 1

        # 4. UNVERIFIABLE
        records.append(
            BenchmarkClaimRecord(
                claim_id=f"{prefix}_{split_tag}_{idx:03d}",
                question=spec.unv_question,
                candidate_claim=spec.unv_claim,
                claimed_value=spec.unv_value,
                claimed_unit=spec.unv_unit,
                numeric_operator="eq",
                scheme=scheme,
                crop_category=spec.crop_category,
                season=spec.season,
                geography=spec.geography,
                qualification=None,
                requested_policy_version=spec.unv_policy_version,
                requested_effective_date=None,
                claim_type="out_of_scope_or_temporal" if spec.unv_policy_version else "out_of_scope_unverifiable",
                gold_verdict=Verdict.UNVERIFIABLE.value,
                gold_evidence_ids=[],
                gold_rationale=spec.unv_rationale or "Unverifiable: out-of-scope parameter or unverified future draft.",
                case_origin=case_origin,
                annotation_status="gold_verified",
                annotator_notes=f"{scheme} benchmark family {spec.family_id}",
                claim_family_id=spec.family_id,
                split=spec.split,
                rule_parameter=spec.unv_rule_parameter or "out_of_scope_parameter",
            )
        )
        idx += 1

    validate_family_split_integrity(records)
    return records


def validate_family_split_integrity(records: list[BenchmarkClaimRecord]) -> None:
    """Assert no claim_family_id appears in more than one split."""
    fam_splits: dict[str, set[str]] = {}
    for rec in records:
        fam_splits.setdefault(rec.claim_family_id, set()).add(rec.split)
    leaks = {fid: sp for fid, sp in fam_splits.items() if len(sp) > 1}
    if leaks:
        raise ValueError(f"Family split leakage detected: {leaks}")


def save_scheme_benchmark_claims(
    scheme: str,
    records: list[BenchmarkClaimRecord],
    project_root: Path | None = None,
) -> Path:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]
    out_path = project_root / "data" / "benchmark" / scheme.lower() / "claims.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    return out_path


def load_scheme_benchmark_claims(
    scheme: str,
    project_root: Path | None = None,
    split: str | None = None,
) -> list[BenchmarkClaimRecord]:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]
    path = project_root / "data" / "benchmark" / scheme.lower() / "claims.jsonl"
    records: list[BenchmarkClaimRecord] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rec = BenchmarkClaimRecord(**d)
            if split is None or rec.split == split:
                records.append(rec)
    return records
