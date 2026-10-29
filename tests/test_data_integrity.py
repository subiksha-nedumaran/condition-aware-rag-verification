"""Tests for source manifest integrity, benchmark split isolation, and schema compliance (Phase 1-4)."""

from __future__ import annotations

from pathlib import Path

from fieldguard.benchmark_builder import load_benchmark_claims
from fieldguard.evidence_schema import validate_structured_rule_record
from fieldguard.evidence_store import build_default_evidence_store
from fieldguard.metadata import validate_evidence_unit_schema
from fieldguard.source_manifest import compute_file_sha256, load_source_manifest, validate_source_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_checksums_and_effective_date_discipline() -> None:
    """Verify SHA-256 checksums match disk files and effective_from is never inferred from publication_date."""
    manifest_path = PROJECT_ROOT / "data" / "manifests" / "source_manifest.json"
    manifest = load_source_manifest(manifest_path)
    assert len(manifest.documents) >= 6

    valid, errs = validate_source_manifest(manifest, PROJECT_ROOT)
    assert valid is True, f"Manifest validation failed: {errs}"

    for doc in manifest.documents:
        fpath = PROJECT_ROOT / doc.local_path
        assert fpath.exists(), f"Missing document on disk: {doc.local_path}"
        actual_sha = compute_file_sha256(fpath)
        assert actual_sha == doc.sha256
        # Verify PIB Dec 2025 announcement has publication_date="2025-12-12" and effective_from=None
        if doc.document_id == "DOC_PIB_2025_PRID2197713":
            assert doc.publication_date == "2025-12-12"
            assert doc.effective_from is None


def test_benchmark_split_isolation_and_verdict_coverage() -> None:
    """Verify >= 200 claims, zero claim_family_id leakage between dev and test, and all 16 categories."""
    all_claims = load_benchmark_claims(PROJECT_ROOT, split=None)
    dev_claims = load_benchmark_claims(PROJECT_ROOT, split="dev")
    test_claims = load_benchmark_claims(PROJECT_ROOT, split="test")

    assert len(all_claims) >= 200
    assert len(dev_claims) + len(test_claims) == len(all_claims)

    dev_families = {c.claim_family_id for c in dev_claims}
    test_families = {c.claim_family_id for c in test_claims}
    assert len(dev_families.intersection(test_families)) == 0, "Family leakage detected between dev and test!"

    verdict_counts: dict[str, int] = {}
    for c in all_claims:
        verdict_counts[c.gold_verdict] = verdict_counts.get(c.gold_verdict, 0) + 1

    assert verdict_counts.get("SUPPORTED", 0) >= 40
    assert verdict_counts.get("WRONG_CONTEXT", 0) >= 40
    assert verdict_counts.get("CONTRADICTED", 0) >= 40
    assert verdict_counts.get("UNVERIFIABLE", 0) >= 30

    claim_types = {c.claim_type for c in all_claims}
    assert len(claim_types) >= 16


def test_evidence_units_and_trusted_rules_schema() -> None:
    """Verify all extracted evidence units and trusted rules pass schema validation and preserve page numbers."""
    store = build_default_evidence_store(PROJECT_ROOT)
    assert len(store.evidence_units) >= 40
    assert len(store.trusted_rules) >= 25

    found_distinct_printed_vs_physical = False
    for unit in store.evidence_units.values():
        valid, errs = validate_evidence_unit_schema(unit.to_dict())
        assert valid is True, f"Evidence unit {unit.evidence_id} failed validation: {errs}"
        if unit.physical_pdf_page is not None and unit.printed_page is not None:
            if str(unit.physical_pdf_page) != str(unit.printed_page):
                found_distinct_printed_vs_physical = True

    assert found_distinct_printed_vs_physical is True

    for rule in store.trusted_rules.values():
        valid_r, errs_r = validate_structured_rule_record(rule)
        assert valid_r is True, f"Trusted rule {rule.rule_id} failed validation: {errs_r}"
