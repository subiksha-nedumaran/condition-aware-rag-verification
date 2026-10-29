"""Cluster-bootstrap confidence intervals and paired statistical comparisons (resampling claim families)."""

from __future__ import annotations

from typing import Any

import numpy as np

from fieldguard.evaluation.metrics import compute_verification_metrics


def compute_cluster_bootstrap_cis(
    claim_family_ids: list[str],
    gold_verdicts: list[str],
    predicted_verdicts: list[str],
    n_iterations: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    """
    Compute non-parametric cluster-bootstrap confidence intervals by resampling
    `claim_family_id` clusters with replacement (Section 13 & 16).
    """
    rng = np.random.default_rng(seed)
    family_to_indices: dict[str, list[int]] = {}
    for idx, fid in enumerate(claim_family_ids):
        family_to_indices.setdefault(fid, []).append(idx)

    unique_families = sorted(family_to_indices.keys())
    n_fams = len(unique_families)

    point_metrics = compute_verification_metrics(gold_verdicts, predicted_verdicts)
    target_keys = (
        "accuracy",
        "macro_f1",
        "false_support_rate",
        "wrong_context_false_support_rate",
        "unverifiable_false_support_rate",
        "coverage",
        "abstention_rate",
    )

    samples: dict[str, list[float]] = {k: [] for k in target_keys}

    for _ in range(n_iterations):
        sampled_fams = rng.choice(unique_families, size=n_fams, replace=True)
        boot_indices: list[int] = []
        for sf in sampled_fams:
            boot_indices.extend(family_to_indices[sf])

        b_gold = [gold_verdicts[i] for i in boot_indices]
        b_pred = [predicted_verdicts[i] for i in boot_indices]
        bm = compute_verification_metrics(b_gold, b_pred)
        for k in target_keys:
            samples[k].append(float(bm[k]))

    alpha = 1.0 - confidence_level
    lo_pct = (alpha / 2.0) * 100.0
    hi_pct = (1.0 - alpha / 2.0) * 100.0

    results: dict[str, dict[str, float]] = {}
    for k in target_keys:
        arr = np.array(samples[k], dtype=np.float64)
        results[k] = {
            "point": round(float(point_metrics[k]), 4),
            "ci_lower": round(float(np.percentile(arr, lo_pct)), 4),
            "ci_upper": round(float(np.percentile(arr, hi_pct)), 4),
            "std_err": round(float(np.std(arr, ddof=1)), 4),
        }
    return results


def compute_paired_cluster_bootstrap_diff(
    claim_family_ids: list[str],
    gold_verdicts: list[str],
    preds_method_a: list[str],
    preds_method_b: list[str],
    n_iterations: int = 1000,
    confidence_level: float = 0.95,
    seed: int = 42,
) -> dict[str, dict[str, Any]]:
    """
    Compare Method A (e.g., Full FieldGuard) vs Method B (a baseline or ablation) on the
    exact same benchmark split using paired cluster-bootstrap resampling over `claim_family_id`.
    Reports delta = Metric(A) - Metric(B) and 95% bootstrap confidence intervals.
    """
    rng = np.random.default_rng(seed)
    family_to_indices: dict[str, list[int]] = {}
    for idx, fid in enumerate(claim_family_ids):
        family_to_indices.setdefault(fid, []).append(idx)

    unique_families = sorted(family_to_indices.keys())
    n_fams = len(unique_families)

    m_a = compute_verification_metrics(gold_verdicts, preds_method_a)
    m_b = compute_verification_metrics(gold_verdicts, preds_method_b)

    target_keys = (
        "accuracy",
        "macro_f1",
        "false_support_rate",
        "wrong_context_false_support_rate",
        "unverifiable_false_support_rate",
    )
    diff_samples: dict[str, list[float]] = {k: [] for k in target_keys}

    for _ in range(n_iterations):
        sampled_fams = rng.choice(unique_families, size=n_fams, replace=True)
        boot_indices: list[int] = []
        for sf in sampled_fams:
            boot_indices.extend(family_to_indices[sf])

        b_gold = [gold_verdicts[i] for i in boot_indices]
        b_pa = [preds_method_a[i] for i in boot_indices]
        b_pb = [preds_method_b[i] for i in boot_indices]

        bma = compute_verification_metrics(b_gold, b_pa)
        bmb = compute_verification_metrics(b_gold, b_pb)
        for k in target_keys:
            diff_samples[k].append(float(bma[k]) - float(bmb[k]))

    alpha = 1.0 - confidence_level
    lo_pct = (alpha / 2.0) * 100.0
    hi_pct = (1.0 - alpha / 2.0) * 100.0

    out: dict[str, dict[str, Any]] = {}
    for k in target_keys:
        arr = np.array(diff_samples[k], dtype=np.float64)
        pt_diff = float(m_a[k]) - float(m_b[k])
        lo = float(np.percentile(arr, lo_pct))
        hi = float(np.percentile(arr, hi_pct))
        ci_excludes_zero = bool((lo > 0.0) or (hi < 0.0))
        out[k] = {
            "method_a": round(float(m_a[k]), 4),
            "method_b": round(float(m_b[k]), 4),
            "delta_a_minus_b": round(pt_diff, 4),
            "ci_lower": round(lo, 4),
            "ci_upper": round(hi, 4),
            "ci_excludes_zero": ci_excludes_zero,
        }
    return out
