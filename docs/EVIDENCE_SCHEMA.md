# FieldGuard Evidence Schema Specification

**Document ID:** `DOC-SCHEMA-002`  
**Version:** 2.0.0 (Stage 2 Generalized Multi-Scheme)  
**Project:** FieldGuard  

---

## 1. Overview and Design Principles

FieldGuard requires structured numerical evidence grounded in authentic government policy sources. In Stage 1, the evidence representation was specialized for crop insurance (`StructuredRuleRecord`). In Stage 2, FieldGuard introduces `GenericEvidenceRecord`, a scheme-agnostic data model that decouples numerical policy rules from specific agricultural terminology (such as crops and seasons) while maintaining backward compatibility with Stage 1.

The evidence schema is designed under five fundamental principles:
1. **Provenance Completeness:** Every rule must be traceable to its exact source document ID, physical PDF page, section, table, row, and extracted passage hash.
2. **Deterministic Typing:** Numerical values, units, operators, and conditions are strictly typed and validated before entry into the evidence store.
3. **Decoupled Predicates:** Conditions and eligibility criteria are represented as key-value predicates and exclusion sets rather than fixed class attributes.
4. **Conservation of Uncertainty:** If an extracted passage contains ambiguous or conflicting rates across official publications, both records are retained and flagged (`conflict_flag = True`).
5. **Bidirectional Translatability:** Full bidirectional compatibility exists between `StructuredRuleRecord` and `GenericEvidenceRecord`.

---

## 2. Core Schemas

### 2.1 `GenericEvidenceRecord`
```python
@dataclass
class GenericEvidenceRecord:
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
```

### 2.2 Field Definitions & Constraints

| Field | Type | Required | Description | Example (PMFBY) | Example (PM-KISAN) |
|---|---|---|---|---|---|
| `rule_id` | `str` | Yes | Unique rule identifier | `RULE_OG2023_KHARIF_2PCT` | `RULE_PMKISAN_ANNUAL_6K` |
| `evidence_id` | `str` | Yes | Extracted evidence unit provenance | `EV_DOC_PMFBY_OG_2023_P5_TBL1_R1` | `EV_DOC_PMKISAN_OG_P5_S2` |
| `scheme` | `str` | Yes | Primary scheme identifier | `PMFBY` | `PM_KISAN` |
| `rule_parameter` | `str` | Yes | Scheme parameter under check | `farmer_premium_rate` | `annual_income_support` |
| `primary_value` | `float` | Yes | Canonical numerical benchmark value | `2.0` | `6000.0` |
| `unit` | `str` | Yes | Standardized unit | `percent` | `rupees` |
| `numeric_operator` | `str` | Yes | Operator (`le`, `ge`, `eq`, `in_set`) | `le` | `eq` |
| `basis` | `str` | Yes | Denominator or calculation basis | `sum_insured` | `per_eligible_farmer_family` |
| `qualifier` | `str` | Yes | Statutory qualification clause | `or_actuarial_rate_whichever_is_less` | `three_equal_instalments_of_2000` |
| `entity_scope` | `str` | Optional | Target group, crop, or entity | `food_grain_and_oilseed` | `all_landholding_farmers` |
| `conditions` | `dict` | Optional | Predicate dictionary | `{"season": "kharif"}` | `{"frequency": "annual"}` |
| `exclusions` | `list` | Optional | Disqualifying attributes | `[]` | `["income_tax_payee", "govt_employee"]` |
| `frequency` | `str` | Optional | Payment frequency | `annual` | `annual` / `per_instalment` |
| `verification_status` | `str` | Yes | Trusted official status | `trusted_official` | `trusted_official` |

---

## 3. Bidirectional Mapping Between Stages

To safeguard existing PMFBY evaluations while enabling PM-KISAN, the following automatic mappings are maintained:

```
StructuredRuleRecord (Stage 1)              GenericEvidenceRecord (Stage 2)
─────────────────────────────────          ─────────────────────────────────
maximum_rate                       <===>   primary_value
season                             <===>   conditions["season"]
crop_category                      <===>   entity_scope / conditions["crop_category"]
qualifier                          <===>   qualifier
basis                              <===>   basis
allowed_values                     <===>   allowed_values
```

Conversion methods:
- `StructuredRuleRecord.to_generic_record() -> GenericEvidenceRecord`
- `GenericEvidenceRecord.to_structured_rule_record() -> StructuredRuleRecord`
- `GenericEvidenceRecord.from_structured_rule_record(record) -> GenericEvidenceRecord`

---

## 4. Integrity Validation Rules

The function `validate_generic_evidence_record(record, known_document_ids, known_evidence_ids)` enforces:
1. All required fields are non-null and non-empty.
2. `primary_value` must be a valid float.
3. `verification_status` must equal `"trusted_official"` for any rule entering the active rule store.
4. `source_document_id` and `evidence_id` must match known manifest IDs when provided.

