"""Unit and adversarial tests for numerical normalization and comparison (Phase 6 & 11)."""

from __future__ import annotations

import pytest

from fieldguard.numeric_normalizer import (
    compare_numeric_values,
    detect_numeric_corruption,
    extract_all_numeric_mentions,
    extract_basis_from_text,
    extract_numeric_operator,
    extract_qualifier_from_text,
    normalize_claim_numerics,
    normalize_unit_and_value,
)


def test_equivalent_percentage_and_word_forms() -> None:
    """Adversarial Case 9: Equivalent percentage and word forms ('2%', '2.0%', 'two percent')."""
    n1 = normalize_claim_numerics("The maximum farmer premium is 2% of Sum Insured.")
    n2 = normalize_claim_numerics("The maximum farmer premium is 2.0% of Sum Insured.")
    n3 = normalize_claim_numerics("The maximum farmer premium is two percent of Sum Insured.")
    n4 = normalize_claim_numerics("The maximum farmer premium is 2 per cent of Sum Insured.")

    assert n1.primary_value == pytest.approx(2.0)
    assert n2.primary_value == pytest.approx(2.0)
    assert n3.primary_value == pytest.approx(2.0)
    assert n4.primary_value == pytest.approx(2.0)
    assert n1.primary_unit == "percent"
    assert n2.primary_unit == "percent"
    assert n3.primary_unit == "percent"
    assert n4.primary_unit == "percent"


def test_one_point_five_percent_word_form() -> None:
    """Verify 'one point five percent' normalizes to 1.5 percent."""
    n = normalize_claim_numerics("The farmer premium is one point five percent of Sum Insured.")
    assert n.primary_value == pytest.approx(1.5)
    assert n.primary_unit == "percent"


def test_equivalent_ratio_and_percentage_forms() -> None:
    """Adversarial Case 10: Equivalent ratio and percentage forms ('50:50' vs '50%', '90:10' vs '90%')."""
    r50 = normalize_claim_numerics("The premium subsidy is shared 50:50 between Centre and State.")
    r90 = normalize_claim_numerics("The premium subsidy is shared 90:10 in North Eastern States.")
    assert r50.primary_value == pytest.approx(50.0)
    assert r50.primary_unit == "percent"
    assert r90.primary_value == pytest.approx(90.0)
    assert r90.primary_unit == "percent"

    ok, _ = compare_numeric_values(50.0, "percent", 50.0, "percent")
    assert ok is True


def test_non_equivalent_percentage_and_decimal_forms() -> None:
    """Adversarial Case 11: Non-equivalent percentage and decimal forms ('2%' vs '0.02%')."""
    n_two_pct = normalize_claim_numerics("The maximum farmer premium is 2% of Sum Insured.")
    n_zero_two_pct = normalize_claim_numerics("The maximum farmer premium is 0.02% of Sum Insured.")
    assert n_two_pct.primary_value == pytest.approx(2.0)
    assert n_zero_two_pct.primary_value == pytest.approx(0.02)

    ok, msg = compare_numeric_values(
        claimed_value=n_zero_two_pct.primary_value or 0.0,
        claimed_unit=n_zero_two_pct.primary_unit or "percent",
        rule_value=n_two_pct.primary_value or 0.0,
        rule_unit=n_two_pct.primary_unit or "percent",
    )
    assert ok is False
    assert "mismatch" in msg.lower()


def test_inequality_and_operator_extraction() -> None:
    """Adversarial Case 12: Inequality claims ('up to 2%', 'at least 2%', 'more than 2%', 'less than 2%')."""
    op_le, uncond_le = extract_numeric_operator("The farmer premium is up to 2% of Sum Insured.")
    assert op_le == "le"
    assert uncond_le is False

    op_ge, _ = extract_numeric_operator("Farmers must pay at least 2% of Sum Insured.")
    assert op_ge == "ge"

    op_gt, _ = extract_numeric_operator("The premium rate is more than 2% of Sum Insured.")
    assert op_gt == "gt"

    op_lt, _ = extract_numeric_operator("The premium rate is less than 2% of Sum Insured.")
    assert op_lt == "lt"

    _, uncond_flat = extract_numeric_operator(
        "A farmer always pays a fixed 2.0% of Sum Insured even when the actuarial rate is lower at 1.2%."
    )
    assert uncond_flat is True


def test_canonical_duration_conversions() -> None:
    """Adversarial Case 13 & Duration Equivalence: '2 weeks' == '14 days', '3 days' == '72 hours'."""
    ok_weeks, _ = compare_numeric_values(2.0, "weeks", 14.0, "days")
    assert ok_weeks is True

    ok_hours, _ = compare_numeric_values(3.0, "days", 72.0, "hours")
    assert ok_hours is True

    ok_wrong_unit, _ = compare_numeric_values(2.0, "hectares", 2.0, "percent")
    assert ok_wrong_unit is False


def test_basis_and_qualifier_extraction() -> None:
    """Verify basis/denominator and qualification extraction."""
    assert extract_basis_from_text("2.0% of Sum Insured") == "sum_insured"
    assert extract_basis_from_text("2.0% of the Threshold Yield") == "threshold_yield"
    assert extract_basis_from_text("0.5% of the Gross Premium") == "gross_premium"
    assert (
        extract_qualifier_from_text("2.0% of Sum Insured or actuarial rate, whichever is less")
        == "or_actuarial_rate_whichever_is_less"
    )
    assert (
        extract_qualifier_from_text("1.5% of Sum Insured or actuarial rate, whichever is higher")
        == "contradictory_whichever_is_higher"
    )


def test_multi_number_disambiguation_and_corruption_detection() -> None:
    """Adversarial Case 25: Multi-number sentence disambiguates condition trigger (75%) from payout (25%)."""
    expr = normalize_claim_numerics(
        "Under the 2023 PMFBY operational guidelines, when more than 75% of sown area is prevented from sowing, farmers are eligible for an on-account payout up to 25.0% of Sum Insured."
    )
    assert expr.primary_value == pytest.approx(25.0)
    assert expr.primary_unit == "percent"
    assert len(expr.secondary_mentions) == 1
    assert expr.secondary_mentions[0].value == pytest.approx(75.0)

    corrupt, _ = detect_numeric_corruption("The rate is 2 . 0 % of Sum Insured.")
    assert corrupt is True
