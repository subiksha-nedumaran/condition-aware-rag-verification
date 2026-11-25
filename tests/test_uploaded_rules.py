"""Upload candidates preserve local bounds without asserting policy semantics."""

import pytest

from fieldguard.uploaded_doc_engine import process_uploaded_document


def candidates(text):
    return process_uploaded_document(text.encode(), "policy.txt")[2]


@pytest.mark.parametrize("phrase,operator,minimum,maximum", [
    ("up to", "le", None, 50), ("at most", "le", None, 50),
    ("not exceeding", "le", None, 50), ("no more than", "le", None, 50),
    ("at least", "ge", 50, None), ("not less than", "ge", 50, None),
    ("less than", "lt", None, 50), ("more than", "gt", 50, None),
    ("exactly", "eq", 50, 50), ("", None, None, None),
])
def test_explicit_bounds(phrase, operator, minimum, maximum):
    rule = candidates(f"Women receive {phrase} 50 percent assistance.")[0]
    assert rule.numeric_operator == operator
    assert rule.minimum_value == minimum
    assert rule.maximum_value == maximum
    assert rule.allowed_values == ([50] if operator == "eq" else None)


def test_operators_do_not_leak_between_mentions():
    rules = candidates("Women receive at least 50 percent assistance or up to Rs 500000, whichever is less.")
    assert [(r.value, r.numeric_operator) for r in rules] == [(50, "ge"), (500000, "le")]
    assert all(r.qualifier == "whichever is less" for r in rules)
    assert all(r.conditions["qualifier_scope"] == "whole_passage" for r in rules)


def test_unknown_second_operator_is_not_inherited():
    rules = candidates("Women receive up to 50 percent assistance; men receive 40 percent assistance.")
    assert [r.numeric_operator for r in rules] == ["le", None]


def test_repeated_mentions_retain_distinct_offsets():
    text = "Women receive up to 50 percent; men receive at least 50 percent."
    rules = candidates(text)
    assert len(rules) == 2
    assert [r.numeric_operator for r in rules] == ["le", "ge"]
    for rule in rules:
        assert text[rule.mention_start:rule.mention_end] == rule.raw_mention


def test_full_eligibility_frequency_and_geography_are_preserved():
    text = "Women landowners in Rajasthan receive up to Rs 5000 per month, only if registered."
    rule = candidates(text)[0]
    assert rule.conditions["source_passage"] == text
    assert rule.conditions["frequency_and_basis_phrases"] == ["per month"]
    assert rule.verification_status == "user_uploaded_unverified"


def test_publication_year_does_not_invent_effective_date():
    rule = candidates("Published in 2026. Women receive up to 50 percent assistance.")[0]
    assert rule.publication_date is None
    assert rule.effective_from is None
    assert rule.effective_to is None
