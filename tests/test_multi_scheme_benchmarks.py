"""Tests for held-out flagship scheme benchmarks and evaluation integrity."""

from __future__ import annotations

from pathlib import Path

import pytest

from fieldguard.benchmarks import (
    SCHEME_BENCHMARK_BUILDERS,
    load_flagship_scheme_benchmark,
    save_all_flagship_scheme_benchmarks,
    validate_family_split_integrity,
)


def test_flagship_benchmark_builders_produce_valid_records():
    for scheme, builder in SCHEME_BENCHMARK_BUILDERS.items():
        records = builder()
        assert len(records) >= 100, f"{scheme} has only {len(records)} records, expected >= 100"
        validate_family_split_integrity(records)


def test_flagship_benchmarks_split_family_leakage_zero():
    for scheme, builder in SCHEME_BENCHMARK_BUILDERS.items():
        records = builder()
        family_splits: dict[str, set[str]] = {}
        for r in records:
            family_splits.setdefault(r.claim_family_id, set()).add(r.split)

        leaked = {fid: splits for fid, splits in family_splits.items() if len(splits) > 1}
        assert not leaked, f"{scheme} has family leakage across splits: {leaked}"


def test_flagship_benchmark_variant_balance():
    expected_variants = {"SUPPORTED", "CONTRADICTED", "WRONG_CONTEXT", "UNVERIFIABLE"}
    for scheme, builder in SCHEME_BENCHMARK_BUILDERS.items():
        records = builder()
        for s in ("train", "dev", "test"):
            split_records = [r for r in records if r.split == s]
            verdicts = {r.gold_verdict for r in split_records}
            assert verdicts == expected_variants, f"{scheme} split {s} missing variants: {expected_variants - verdicts}"


def test_flagship_benchmark_persistence_and_loading(tmp_path: Path):
    saved_paths = save_all_flagship_scheme_benchmarks(project_root=tmp_path)
    for scheme, p in saved_paths.items():
        assert p.exists()
        loaded = load_flagship_scheme_benchmark(scheme, project_root=tmp_path)
        assert len(loaded) >= 100
        test_loaded = load_flagship_scheme_benchmark(scheme, project_root=tmp_path, split="test")
        assert len(test_loaded) == 40
