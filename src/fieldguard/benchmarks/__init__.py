"""Multi-scheme held-out claim-family benchmarks."""

from __future__ import annotations

from pathlib import Path

from fieldguard.benchmarks.common import (
    ClaimFamilySpec,
    expand_family_specs,
    load_scheme_benchmark_claims,
    save_scheme_benchmark_claims,
    validate_family_split_integrity,
)
from fieldguard.benchmarks.mgnrega_claims import (
    build_mgnrega_benchmark_claims,
    load_mgnrega_benchmark_claims,
    save_mgnrega_benchmark_claims,
)
from fieldguard.benchmarks.pm_jay_claims import (
    build_pm_jay_benchmark_claims,
    load_pm_jay_benchmark_claims,
    save_pm_jay_benchmark_claims,
)
from fieldguard.benchmarks.pm_kusum_claims import (
    build_pm_kusum_benchmark_claims,
    load_pm_kusum_benchmark_claims,
    save_pm_kusum_benchmark_claims,
)
from fieldguard.benchmarks.pmay_g_claims import (
    build_pmay_g_benchmark_claims,
    load_pmay_g_benchmark_claims,
    save_pmay_g_benchmark_claims,
)
from fieldguard.benchmarks.pmmy_claims import (
    build_pmmy_benchmark_claims,
    load_pmmy_benchmark_claims,
    save_pmmy_benchmark_claims,
)
from fieldguard.benchmark_builder import BenchmarkClaimRecord

SCHEME_BENCHMARK_BUILDERS = {
    "MGNREGA": build_mgnrega_benchmark_claims,
    "PM_JAY": build_pm_jay_benchmark_claims,
    "PMAY_G": build_pmay_g_benchmark_claims,
    "PM_KUSUM": build_pm_kusum_benchmark_claims,
    "PMMY": build_pmmy_benchmark_claims,
}


def save_all_flagship_scheme_benchmarks(project_root: Path | None = None) -> dict[str, Path]:
    """Build and save held-out benchmark JSONL files for all 5 flagship schemes."""
    paths: dict[str, Path] = {}
    for scheme, builder in SCHEME_BENCHMARK_BUILDERS.items():
        records = builder()
        validate_family_split_integrity(records)
        paths[scheme] = save_scheme_benchmark_claims(scheme, records, project_root=project_root)
    return paths


def load_flagship_scheme_benchmark(
    scheme: str,
    project_root: Path | None = None,
    split: str | None = None,
) -> list[BenchmarkClaimRecord]:
    return load_scheme_benchmark_claims(scheme, project_root=project_root, split=split)


__all__ = [
    "ClaimFamilySpec",
    "SCHEME_BENCHMARK_BUILDERS",
    "build_mgnrega_benchmark_claims",
    "build_pm_jay_benchmark_claims",
    "build_pm_kusum_benchmark_claims",
    "build_pmay_g_benchmark_claims",
    "build_pmmy_benchmark_claims",
    "expand_family_specs",
    "load_flagship_scheme_benchmark",
    "load_mgnrega_benchmark_claims",
    "load_pm_jay_benchmark_claims",
    "load_pm_kusum_benchmark_claims",
    "load_pmay_g_benchmark_claims",
    "load_pmmy_benchmark_claims",
    "load_scheme_benchmark_claims",
    "save_all_flagship_scheme_benchmarks",
    "save_mgnrega_benchmark_claims",
    "save_pm_jay_benchmark_claims",
    "save_pm_kusum_benchmark_claims",
    "save_pmay_g_benchmark_claims",
    "save_pmmy_benchmark_claims",
    "save_scheme_benchmark_claims",
    "validate_family_split_integrity",
]
