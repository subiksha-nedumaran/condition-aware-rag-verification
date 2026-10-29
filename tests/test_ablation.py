"""Tests verifying that each ablation configuration genuinely disables its target component (Phase 9)."""

from __future__ import annotations

from pathlib import Path

from fieldguard.evaluation.ablation import get_ablation_configurations
from fieldguard.evaluation.runner import build_all_retrievers
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.verdicts import Verdict
from fieldguard.verifier import FieldGuardVerifier, VerifierConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ablation_configs_cover_all_11_settings() -> None:
    configs = get_ablation_configurations()
    assert len(configs) == 11
    names = [c.config_name for c in configs]
    assert "full_fieldguard" in names
    assert "no_structured_condition_matching" in names
    assert "no_crop_category_matching" in names
    assert "no_season_matching" in names
    assert "no_qualification_matching" in names
    assert "no_temporal_checks" in names
    assert "no_provenance_validation" in names
    assert "no_evidence_sufficiency" in names
    assert "no_hybrid_retrieval" in names


def test_ablation_disables_crop_category_matching_on_kharif_5_percent() -> None:
    """Disabling crop_category_matching causes Kharif 5% claim to match the 5% commercial crop rule."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)

    q = "Under the 2023 PMFBY operational guidelines, for Kharif food grains, is the maximum farmer premium 5%?"
    c = "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food-grain and oilseed crops is 5.0% of Sum Insured or actuarial rate, whichever is less."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]

    v_full = FieldGuardVerifier(store, VerifierConfig(config_name="full_fieldguard"))
    res_full = v_full.verify_claim("ABL_FULL_CROP", q, c, ret_items)
    assert res_full.predicted_verdict == Verdict.WRONG_CONTEXT.value

    v_no_crop = FieldGuardVerifier(
        store,
        VerifierConfig(config_name="no_crop_category_matching", enable_crop_category_matching=False),
    )
    res_no_crop = v_no_crop.verify_claim("ABL_NO_CROP", q, c, ret_items)
    assert res_no_crop.predicted_verdict == Verdict.SUPPORTED.value


def test_ablation_disables_season_matching_on_kharif_1_5_percent() -> None:
    """Disabling season_matching causes Kharif 1.5% claim to match the 1.5% Rabi food-grain rule."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)

    q = "Under the 2023 PMFBY operational guidelines, for Kharif food-grain and oilseed crops, is the maximum farmer premium 1.5%?"
    c = "Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food-grain and oilseed crops is 1.5% of Sum Insured or actuarial rate, whichever is less."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]

    v_full = FieldGuardVerifier(store, VerifierConfig(config_name="full_fieldguard"))
    assert v_full.verify_claim("ABL_FULL_SEAS", q, c, ret_items).predicted_verdict == Verdict.WRONG_CONTEXT.value

    v_no_seas = FieldGuardVerifier(
        store,
        VerifierConfig(config_name="no_season_matching", enable_season_matching=False),
    )
    assert v_no_seas.verify_claim("ABL_NO_SEAS", q, c, ret_items).predicted_verdict == Verdict.SUPPORTED.value


def test_ablation_disables_qualification_matching() -> None:
    """Disabling qualification_matching causes an unconditional 2.0% flat claim to be falsely SUPPORTED."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)

    q = "Under the 2023 PMFBY operational guidelines, does a Kharif food-grain farmer always pay a flat 2.0% premium even if the actuarial rate is 1.2%?"
    c = "Under the 2023 PMFBY operational guidelines, a Kharif food-grain farmer always pays a fixed 2.0% of Sum Insured even when the actuarial rate is lower at 1.2%."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]

    v_full = FieldGuardVerifier(store, VerifierConfig(config_name="full_fieldguard"))
    assert v_full.verify_claim("ABL_FULL_QUAL", q, c, ret_items).predicted_verdict == Verdict.CONTRADICTED.value

    v_no_qual = FieldGuardVerifier(
        store,
        VerifierConfig(config_name="no_qualification_matching", enable_qualification_matching=False),
    )
    assert v_no_qual.verify_claim("ABL_NO_QUAL", q, c, ret_items).predicted_verdict == Verdict.SUPPORTED.value


def test_ablation_disables_temporal_version_checking() -> None:
    """Disabling temporal checks causes a 2023 historical rule to be accepted as current 2026 policy."""
    store = build_default_evidence_store(PROJECT_ROOT)
    retrievers = build_all_retrievers(store)

    q = "Under the latest current 2026 revised PMFBY operational guidelines, is the maximum farmer premium for Kharif food grains still 2.0%?"
    c = "Under the latest current 2026 revised PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured."
    ret_items = [r.to_dict() for r in retrievers["hybrid"].retrieve(f"{q} {c}", top_k=5)]

    v_full = FieldGuardVerifier(store, VerifierConfig(config_name="full_fieldguard"))
    assert v_full.verify_claim("ABL_FULL_TEMP", q, c, ret_items).predicted_verdict == Verdict.UNVERIFIABLE.value

    v_no_temp = FieldGuardVerifier(
        store,
        VerifierConfig(config_name="no_temporal_checks", enable_temporal_checks=False),
    )
    assert v_no_temp.verify_claim("ABL_NO_TEMP", q, c, ret_items).predicted_verdict == Verdict.SUPPORTED.value
