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

REQUIRED_GENERIC_EVIDENCE_FIELDS: tuple[str, ...] = (
    "rule_id",
    "evidence_id",
    "scheme",
    "rule_parameter",
    "primary_value",
    "unit",
    "basis",
    "qualifier",
    "source_document_id",
    "document_version",
    "section",
    "physical_pdf_page",
    "verification_status",
)


@dataclass
class StructuredRuleRecord:
    """
    Verified structured representation of a numerical policy rule linked to
    its exact source document, page, section, and extracted evidence unit.
    Includes backward-compatible fields for Stage 1 (season, crop_category)
    as well as generalized condition attributes for Stage 2.
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
    # Stage 2 generalized condition attributes
    entity_scope: str | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    exclusions: list[str] = field(default_factory=list)
    frequency: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_generic_record(self) -> GenericEvidenceRecord:
        """Convert this StructuredRuleRecord into a scheme-agnostic GenericEvidenceRecord."""
        conds = dict(self.conditions)
        if self.season and "season" not in conds:
            conds["season"] = self.season
        if self.crop_category and "crop_category" not in conds:
            conds["crop_category"] = self.crop_category

        return GenericEvidenceRecord(
            rule_id=self.rule_id,
            evidence_id=self.evidence_id,
            scheme=self.scheme,
            rule_parameter=self.rule_parameter,
            primary_value=self.maximum_rate,
            unit=self.unit,
            minimum_value=self.minimum_value,
            allowed_values=list(self.allowed_values) if self.allowed_values else None,
            numeric_operator=self.numeric_operator,
            basis=self.basis,
            qualifier=self.qualifier,
            requires_qualifier_for_unconditional_claim=self.requires_qualifier_for_unconditional_claim,
            entity_scope=self.entity_scope or self.crop_category,
            conditions=conds,
            exclusions=list(self.exclusions),
            frequency=self.frequency,
            geography=self.geography,
            source_document_id=self.source_document_id,
            document_version=self.document_version,
            policy_era=self.policy_era,
            publication_date=self.publication_date,
            section=self.section,
            physical_pdf_page=self.physical_pdf_page,
            printed_page=self.printed_page,
            table_id=self.table_id,
            row_id=self.row_id,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verification_status=self.verification_status,
            conflict_flag=self.conflict_flag,
            conflicting_rule_ids=list(self.conflicting_rule_ids),
        )


@dataclass
class GenericEvidenceRecord:
    """
    Scheme-agnostic structured evidence representation for Multi-Scheme FieldGuard (Stage 2).
    Decouples policy rules from PMFBY-specific concepts (crop category, season) by using
    generalized entity scope, condition dictionaries, exclusions, and frequency.
    """

    rule_id: str
    evidence_id: str
    scheme: str
    rule_parameter: str
    primary_value: float
    unit: str
    minimum_value: float | None = None
    allowed_values: list[float] | None = None
    numeric_operator: str = "eq"
    basis: str = ""
    qualifier: str = ""
    requires_qualifier_for_unconditional_claim: bool = False
    entity_scope: str | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    exclusions: list[str] = field(default_factory=list)
    frequency: str | None = None
    geography: str | None = "all_india"
    source_document_id: str = ""
    document_version: str = ""
    policy_era: str = ""
    publication_date: str | None = None
    section: str = ""
    physical_pdf_page: int | None = None
    printed_page: str | None = None
    table_id: str | None = None
    row_id: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    verification_status: str = "trusted_official"
    conflict_flag: bool = False
    conflicting_rule_ids: list[str] = field(default_factory=list)

    @property
    def maximum_rate(self) -> float:
        """Alias for backward compatibility with StructuredRuleRecord."""
        return self.primary_value

    @property
    def season(self) -> str | None:
        """Compatibility accessor for legacy season condition."""
        return self.conditions.get("season")

    @property
    def crop_category(self) -> str | None:
        """Compatibility accessor for legacy crop_category."""
        return self.conditions.get("crop_category") or self.entity_scope

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_structured_rule_record(self) -> StructuredRuleRecord:
        """Convert to legacy StructuredRuleRecord for backward compatibility."""
        return StructuredRuleRecord(
            rule_id=self.rule_id,
            evidence_id=self.evidence_id,
            scheme=self.scheme,
            rule_parameter=self.rule_parameter,
            season=self.conditions.get("season"),
            crop_category=self.conditions.get("crop_category") or self.entity_scope,
            geography=self.geography,
            minimum_value=self.minimum_value,
            maximum_rate=self.primary_value,
            allowed_values=list(self.allowed_values) if self.allowed_values else None,
            numeric_operator=self.numeric_operator,
            unit=self.unit,
            basis=self.basis,
            qualifier=self.qualifier,
            requires_qualifier_for_unconditional_claim=self.requires_qualifier_for_unconditional_claim,
            source_document_id=self.source_document_id,
            document_version=self.document_version,
            policy_era=self.policy_era,
            publication_date=self.publication_date,
            section=self.section,
            physical_pdf_page=self.physical_pdf_page,
            printed_page=self.printed_page,
            table_id=self.table_id,
            row_id=self.row_id,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            verification_status=self.verification_status,
            conflict_flag=self.conflict_flag,
            conflicting_rule_ids=list(self.conflicting_rule_ids),
            entity_scope=self.entity_scope,
            conditions=dict(self.conditions),
            exclusions=list(self.exclusions),
            frequency=self.frequency,
        )

    @classmethod
    def from_structured_rule_record(cls, record: StructuredRuleRecord) -> GenericEvidenceRecord:
        return record.to_generic_record()


def validate_generic_evidence_record(
    record: GenericEvidenceRecord | dict[str, Any],
    known_document_ids: set[str] | None = None,
    known_evidence_ids: set[str] | None = None,
) -> tuple[bool, list[str]]:
    """Validate a GenericEvidenceRecord for schema completeness, provenance, and trusted status."""
    d = record.to_dict() if isinstance(record, GenericEvidenceRecord) else dict(record)
    errors: list[str] = []

    for req in REQUIRED_GENERIC_EVIDENCE_FIELDS:
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
    if d.get("primary_value") is None:
        errors.append(f"Rule {d.get('rule_id')} has null primary_value")
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
