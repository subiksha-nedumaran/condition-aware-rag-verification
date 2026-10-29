"""Mandatory verdict definitions, precedence rules, and decision logic for FieldGuard."""

from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    """The four externally reported verdicts required by FieldGuard."""

    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    WRONG_CONTEXT = "WRONG_CONTEXT"
    UNVERIFIABLE = "UNVERIFIABLE"


ALL_VERDICTS: tuple[str, ...] = (
    Verdict.SUPPORTED.value,
    Verdict.CONTRADICTED.value,
    Verdict.WRONG_CONTEXT.value,
    Verdict.UNVERIFIABLE.value,
)

VERDICT_DEFINITIONS: dict[str, str] = {
    Verdict.SUPPORTED.value: (
        "Applicable trusted official evidence establishes the numerical claim, including "
        "the required semantic context (scheme, crop category, season, geography), unit, "
        "basis/denominator, comparison operator, qualification, and temporal applicability."
    ),
    Verdict.CONTRADICTED.value: (
        "Applicable trusted official evidence for the requested context establishes an "
        "incompatible numerical value, unit, basis/denominator, comparison operator, or "
        "violates a mandatory qualification (such as claiming a flat unconditional rate "
        "when the rule requires 'or actuarial rate, whichever is less')."
    ),
    Verdict.WRONG_CONTEXT.value: (
        "Retrieved evidence contains the claimed numerical value, but demonstrates that "
        "the value belongs to a different crop category, season, geography, or unrelated "
        "operational parameter (e.g., applying the 5% commercial-crop rate to Kharif food "
        "grains, or the 2% Kharif rate to Rabi crops)."
    ),
    Verdict.UNVERIFIABLE.value: (
        "Available evidence is insufficient, absent from retrieved results, ambiguous, "
        "conflicting across official sources, derived from an unverified source, missing "
        "a required condition in the claim, or temporally unresolved (e.g., asking for "
        "the latest/current policy when only historical or partial announcement evidence exists)."
    ),
}


def is_abstention_verdict(verdict: str) -> bool:
    """Return True if the verdict represents an abstention / refusal to assert truth or falsity."""
    return verdict == Verdict.UNVERIFIABLE.value
