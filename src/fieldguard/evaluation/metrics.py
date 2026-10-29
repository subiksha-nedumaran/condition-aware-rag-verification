"""Verification evaluation metrics: accuracy, macro-F1, per-class metrics, confusion matrix, and false-support rates."""

from __future__ import annotations

import numpy as np
from typing import Any

from fieldguard.verdicts import ALL_VERDICTS, Verdict


def compute_verification_metrics(
    gold_verdicts: list[str],
    predicted_verdicts: list[str],
    verification_latencies_ms: list[float] | None = None,
    e2e_latencies_ms: list[float] | None = None,
    config_name: str = "fieldguard_full",
) -> dict[str, Any]:
    """
    Compute comprehensive verification performance metrics required by Phase 9 and Phase 12.
    Explicitly separates:
      - False-Support Rate (FSR) = P(pred == SUPPORTED | gold != SUPPORTED)
      - Wrong-Context False-Support Rate = P(pred == SUPPORTED | gold == WRONG_CONTEXT)
      - Unverifiable False-Support Rate = P(pred == SUPPORTED | gold == UNVERIFIABLE)
      - Contradicted False-Support Rate = P(pred == SUPPORTED | gold == CONTRADICTED)
      - Incorrect-Among-Supported (1 - Precision_SUPPORTED) = P(gold != SUPPORTED | pred == SUPPORTED)
    """
    n = len(gold_verdicts)
    if n == 0 or len(predicted_verdicts) != n:
        raise ValueError("gold_verdicts and predicted_verdicts must be non-empty and of equal length.")

    correct = sum(1 for g, p in zip(gold_verdicts, predicted_verdicts) if g == p)
    accuracy = correct / float(n)

    # Per-class precision, recall, F1, and support
    per_class: dict[str, dict[str, Any]] = {}
    f1_list: list[float] = []

    for label in ALL_VERDICTS:
        tp = sum(1 for g, p in zip(gold_verdicts, predicted_verdicts) if g == label and p == label)
        fp = sum(1 for g, p in zip(gold_verdicts, predicted_verdicts) if g != label and p == label)
        fn = sum(1 for g, p in zip(gold_verdicts, predicted_verdicts) if g == label and p != label)
        support = tp + fn
        pred_count = tp + fp

        prec = tp / float(pred_count) if pred_count > 0 else 0.0
        rec = tp / float(support) if support > 0 else 0.0
        f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)

        per_class[label] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
            "predicted_count": pred_count,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    macro_f1 = sum(f1_list) / float(len(ALL_VERDICTS))

    # 4x4 Confusion Matrix: rows = gold, cols = predicted
    confusion_matrix: dict[str, dict[str, int]] = {
        g_lbl: {p_lbl: 0 for p_lbl in ALL_VERDICTS} for g_lbl in ALL_VERDICTS
    }
    for g, p in zip(gold_verdicts, predicted_verdicts):
        if g in confusion_matrix and p in confusion_matrix[g]:
            confusion_matrix[g][p] += 1

    # False-support rate (FSR) = non-SUPPORTED gold cases predicted SUPPORTED / all non-SUPPORTED gold cases
    non_sup_indices = [i for i, g in enumerate(gold_verdicts) if g != Verdict.SUPPORTED.value]
    fsr_den = len(non_sup_indices)
    fsr_num = sum(
        1 for i in non_sup_indices if predicted_verdicts[i] == Verdict.SUPPORTED.value
    )
    false_support_rate = (fsr_num / float(fsr_den)) if fsr_den > 0 else 0.0

    # False-support rate on WRONG_CONTEXT cases
    wc_indices = [i for i, g in enumerate(gold_verdicts) if g == Verdict.WRONG_CONTEXT.value]
    wc_fsr_den = len(wc_indices)
    wc_fsr_num = sum(
        1 for i in wc_indices if predicted_verdicts[i] == Verdict.SUPPORTED.value
    )
    wc_false_support_rate = (wc_fsr_num / float(wc_fsr_den)) if wc_fsr_den > 0 else 0.0

    # False-support rate on UNVERIFIABLE cases
    unv_indices = [i for i, g in enumerate(gold_verdicts) if g == Verdict.UNVERIFIABLE.value]
    unv_fsr_den = len(unv_indices)
    unv_fsr_num = sum(
        1 for i in unv_indices if predicted_verdicts[i] == Verdict.SUPPORTED.value
    )
    unv_false_support_rate = (unv_fsr_num / float(unv_fsr_den)) if unv_fsr_den > 0 else 0.0

    # False-support rate on CONTRADICTED cases
    con_indices = [i for i, g in enumerate(gold_verdicts) if g == Verdict.CONTRADICTED.value]
    con_fsr_den = len(con_indices)
    con_fsr_num = sum(
        1 for i in con_indices if predicted_verdicts[i] == Verdict.SUPPORTED.value
    )
    con_false_support_rate = (con_fsr_num / float(con_fsr_den)) if con_fsr_den > 0 else 0.0

    # Separate precision-related quantity: fraction of SUPPORTED predictions that are incorrect
    sup_pred_indices = [i for i, p in enumerate(predicted_verdicts) if p == Verdict.SUPPORTED.value]
    sup_pred_den = len(sup_pred_indices)
    sup_pred_false_num = sum(
        1 for i in sup_pred_indices if gold_verdicts[i] != Verdict.SUPPORTED.value
    )
    false_discovery_among_supported = (
        sup_pred_false_num / float(sup_pred_den) if sup_pred_den > 0 else 0.0
    )

    # Abstention rate and Coverage
    abstain_count = sum(1 for p in predicted_verdicts if p == Verdict.UNVERIFIABLE.value)
    abstention_rate = abstain_count / float(n)
    coverage = 1.0 - abstention_rate

    ver_lat = verification_latencies_ms or [0.0] * n
    e2e_lat = e2e_latencies_ms or [0.0] * n

    return {
        "config_name": config_name,
        "n_claims": n,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "false_support_rate": round(false_support_rate, 4),
        "false_support_num": fsr_num,
        "false_support_den": fsr_den,
        "wrong_context_false_support_rate": round(wc_false_support_rate, 4),
        "wrong_context_false_support_num": wc_fsr_num,
        "wrong_context_false_support_den": wc_fsr_den,
        "unverifiable_false_support_rate": round(unv_false_support_rate, 4),
        "unverifiable_false_support_num": unv_fsr_num,
        "unverifiable_false_support_den": unv_fsr_den,
        "contradicted_false_support_rate": round(con_false_support_rate, 4),
        "contradicted_false_support_num": con_fsr_num,
        "contradicted_false_support_den": con_fsr_den,
        "false_discovery_among_supported": round(false_discovery_among_supported, 4),
        "coverage": round(coverage, 4),
        "abstention_rate": round(abstention_rate, 4),
        "supported_precision": per_class[Verdict.SUPPORTED.value]["precision"],
        "supported_recall": per_class[Verdict.SUPPORTED.value]["recall"],
        "supported_f1": per_class[Verdict.SUPPORTED.value]["f1"],
        "contradicted_precision": per_class[Verdict.CONTRADICTED.value]["precision"],
        "contradicted_recall": per_class[Verdict.CONTRADICTED.value]["recall"],
        "contradicted_f1": per_class[Verdict.CONTRADICTED.value]["f1"],
        "wrong_context_precision": per_class[Verdict.WRONG_CONTEXT.value]["precision"],
        "wrong_context_recall": per_class[Verdict.WRONG_CONTEXT.value]["recall"],
        "wrong_context_f1": per_class[Verdict.WRONG_CONTEXT.value]["f1"],
        "unverifiable_precision": per_class[Verdict.UNVERIFIABLE.value]["precision"],
        "unverifiable_recall": per_class[Verdict.UNVERIFIABLE.value]["recall"],
        "unverifiable_f1": per_class[Verdict.UNVERIFIABLE.value]["f1"],
        "verification_latency_mean_ms": round(float(np.mean(ver_lat)), 4),
        "verification_latency_median_ms": round(float(np.median(ver_lat)), 4),
        "verification_latency_p95_ms": round(float(np.percentile(ver_lat, 95)), 4),
        "e2e_latency_mean_ms": round(float(np.mean(e2e_lat)), 4),
        "e2e_latency_median_ms": round(float(np.median(e2e_lat)), 4),
        "e2e_latency_p95_ms": round(float(np.percentile(e2e_lat, 95)), 4),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix,
    }
