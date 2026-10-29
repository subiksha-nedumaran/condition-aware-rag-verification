"""Structured numerical rule schema and integrity validation for Phase 4."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

REQUIRED_STRUCTURED_RULE_FIELDS: tuple[str, ...] = (
    "rule_id",
    "scheme",
    "season",
    "crop_category",
    "minimum_value",
    "maximum_rate",
    "unit",
    "basis",
    "qualifier",
    "source_document_id",
    "document_version",
    "section",
    "physical_pdf_page",
    "printed_page",
    "table_id",
    "row_id",
    "effective_from",
    "effective_to",
    "verification_status",
)


@dataclass
class StructuredRuleRecord:
    """
    Verified structured representation of a numerical policy rule linked to
    its exact source document, page, section, and extracted evidence unit.
    """

    rule_id: str
    evidence_id: str
    scheme: str
    rule_parameter: str
    season: str | None
    crop_category: str | None
    geography: str | None
    minimum_value: float | None
    maximum_rate: float
    allowed_values: list[float] | None
    numeric_operator: str
    unit: str
    basis: str
    qualifier: str
    requires_qualifier_for_unconditional_claim: bool
    source_document_id: str
    document_version: str
    policy_era: str
    publication_date: str | None
    section: str
    physical_pdf_page: int | None
    printed_page: str | None
    table_id: str | None
    row_id: str | None
    effective_from: str | None
    effective_to: str | None
    verification_status: str
    conflict_flag: bool = False
    conflicting_rule_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_structured_rule_record(
    record: StructuredRuleRecord | dict[str, Any],
    known_document_ids: set[str] | None = None,
    known_evidence_ids: set[str] | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate a StructuredRuleRecord for schema completeness, provenance presence,
    and trusted verification status.
    """
    d = record.to_dict() if isinstance(record, StructuredRuleRecord) else dict(record)
    errors: list[str] = []

    for req in REQUIRED_STRUCTURED_RULE_FIELDS:
        if req not in d:
            errors.append(f"Missing required field '{req}' in rule_id={d.get('rule_id')}")

    if not d.get("rule_id"):
        errors.append("Empty rule_id")
    if not d.get("evidence_id"):
        errors.append(f"Rule {d.get('rule_id')} is missing evidence_id provenance")
    if not d.get("source_document_id"):
        errors.append(f"Rule {d.get('rule_id')} is missing source_document_id")
    if not d.get("section"):
        errors.append(f"Rule {d.get('rule_id')} is missing section reference")
    if d.get("maximum_rate") is None:
        errors.append(f"Rule {d.get('rule_id')} has null maximum_rate")
    if not d.get("unit"):
        errors.append(f"Rule {d.get('rule_id')} is missing unit")
    if not d.get("basis"):
        errors.append(f"Rule {d.get('rule_id')} is missing basis/denominator")
    if not d.get("qualifier"):
        errors.append(f"Rule {d.get('rule_id')} is missing mandatory qualifier")

    if d.get("verification_status") != "trusted_official":
        errors.append(
            f"Rule {d.get('rule_id')} has non-trusted verification_status='{d.get('verification_status')}'"
        )

    if known_document_ids is not None and d.get("source_document_id") not in known_document_ids:
        errors.append(
            f"Rule {d.get('rule_id')} references unknown source_document_id='{d.get('source_document_id')}'"
        )

    if known_evidence_ids is not None and d.get("evidence_id") not in known_evidence_ids:
        errors.append(
            f"Rule {d.get('rule_id')} references unknown evidence_id='{d.get('evidence_id')}'"
        )

    return len(errors) == 0, errors
