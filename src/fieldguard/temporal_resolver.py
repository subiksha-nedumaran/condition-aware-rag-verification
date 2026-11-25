"""Temporal applicability and policy-version resolution for FieldGuard (Section 10.4)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fieldguard.claim_parser import ParsedClaim
from fieldguard.evidence_schema import StructuredRuleRecord


@dataclass
class TemporalResolutionResult:
    """Outcome of checking whether a rule or evidence unit satisfies the requested temporal scope."""

    is_applicable: bool
    temporal_status: str
    explanation: str
    requires_abstention: bool = False
    is_version_mismatch: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _date_in_window(
    target_date: str,
    effective_from: str | None,
    effective_to: str | None,
) -> tuple[bool, str]:
    if effective_from is None:
        return False, "Rule effective_from date is unknown (null); cannot verify date-specific applicability."
    if target_date < effective_from:
        return False, f"Requested date {target_date} precedes rule effective_from ({effective_from})."
    if effective_to is not None and target_date > effective_to:
        return False, f"Requested date {target_date} is after rule effective_to ({effective_to})."
    return True, f"Requested date {target_date} falls within [{effective_from}, {effective_to or 'present'}]."


def resolve_temporal_applicability(
    claim: ParsedClaim,
    rule: StructuredRuleRecord,
    enable_temporal_checks: bool = True,
) -> TemporalResolutionResult:
    """
    Evaluate whether `rule` is temporally applicable to `claim`.
    Rules enforced:
    1. Never infer an effective date merely from a publication date.
    2. Distinguish 2016 historical guidelines (2016-04-01 to 2020-03-31) from 2023 revamped guidelines.
    3. Do not assume the 2023 rule establishes unverified 2026 / post-Dec-2025 full revised guidelines.
    4. Undated FAQs/portals with null effective_from cannot alone establish version-specific or date-specific rules.
    """
    if not enable_temporal_checks:
        return TemporalResolutionResult(
            is_applicable=True,
            temporal_status="temporal_checks_disabled",
            explanation="Temporal applicability checks disabled by ablation configuration.",
            requires_abstention=False,
            is_version_mismatch=False,
        )

    req_ver = claim.requested_policy_version
    req_date = claim.requested_effective_date

    # Case 1: Claim asks for an effective date of the Dec 2025 PIB announcement (which has publication_date=2025-12-12 but effective_from=None)
    if rule.policy_era == "announcement_2025_dec" and req_date is not None:
        return TemporalResolutionResult(
            is_applicable=False,
            temporal_status="unresolved_effective_date_not_inferred_from_publication",
            explanation=(
                f"Document {rule.source_document_id} has publication_date={rule.publication_date} "
                f"but effective_from=None. FieldGuard never infers an effective date from a publication date."
            ),
            requires_abstention=True,
            is_version_mismatch=False,
        )

    # Case 2: Claim asks for full post-December 2025 / 2026 revised guidelines or unverified current policy
    if req_ver in (
        "latest_current",
        "2026_revised_full_unverified",
        "2025_dec_full_guidelines_unverified",
        "2028_unverified_draft",
    ):
        return TemporalResolutionResult(
            is_applicable=False,
            temporal_status="unresolved_latest_policy_version",
            explanation=(
                "The query requests the latest current / post-December 2025 revised policy rule. "
                "Only the 2023 Operational Guidelines and a December 2025 PIB loss-assessment announcement "
                "(PRID=2197713, without a complete revised premium schedule or effective date) are verified; "
                "FieldGuard refuses to assume the 2023 historical rule is current without qualification."
            ),
            requires_abstention=True,
            is_version_mismatch=False,
        )

    # Case 3: Explicit requested_effective_date
    if req_date is not None:
        ok, msg = _date_in_window(req_date, rule.effective_from, rule.effective_to)
        if not ok:
            is_mismatch = rule.effective_from is not None
            return TemporalResolutionResult(
                is_applicable=False,
                temporal_status="date_outside_effective_window" if is_mismatch else "missing_effective_date",
                explanation=msg,
                requires_abstention=not is_mismatch,
                is_version_mismatch=is_mismatch,
            )

    # Case 4: Explicit requested_policy_version == '2016_historical'
    if req_ver == "2016_historical":
        if rule.policy_era == "historical_2016":
            return TemporalResolutionResult(
                is_applicable=True,
                temporal_status="matched_2016_historical_version",
                explanation="Rule matches requested 2016 Historical Operational Guidelines (2016-2020).",
            )
        return TemporalResolutionResult(
            is_applicable=False,
            temporal_status="policy_version_mismatch_expected_2016",
            explanation=f"Claim requests 2016 historical guidelines, but rule belongs to '{rule.policy_era}'.",
            requires_abstention=False,
            is_version_mismatch=True,
        )

    # Case 5: Explicit requested_policy_version == '2025_dec_announcement'
    if req_ver == "2025_dec_announcement":
        if rule.policy_era == "announcement_2025_dec":
            return TemporalResolutionResult(
                is_applicable=True,
                temporal_status="matched_2025_dec_announcement",
                explanation="Rule matches the December 2025 PIB Press Release (PRID=2197713).",
            )
        return TemporalResolutionResult(
            is_applicable=False,
            temporal_status="policy_version_mismatch_expected_2025_announcement",
            explanation=f"Claim asks about the Dec 2025 PIB announcement, but rule is from '{rule.policy_era}'.",
            requires_abstention=False,
            is_version_mismatch=True,
        )

    # Case 6: Explicit requested_policy_version == '2023_guidelines' or default 2023 guideline evaluation
    if req_ver in ("2023_guidelines", None):
        if rule.policy_era == "guidelines_2023":
            return TemporalResolutionResult(
                is_applicable=True,
                temporal_status="matched_2023_guidelines",
                explanation="Rule is verified in the 2023 PMFBY Revamped Operational Guidelines.",
            )
        if rule.policy_era == "historical_2016":
            return TemporalResolutionResult(
                is_applicable=False,
                temporal_status="superseded_2016_historical_rule",
                explanation=(
                    "Rule is from the superseded 2016 Operational Guidelines (effective_to=2020-03-31) "
                    "and cannot establish a 2023 Revamped Operational Guidelines claim."
                ),
                requires_abstention=False,
                is_version_mismatch=True,
            )
        if rule.policy_era in ("faq_undated", "portal_undated"):
            if req_ver == "2023_guidelines":
                return TemporalResolutionResult(
                    is_applicable=False,
                    temporal_status="undated_faq_cannot_verify_dated_guideline_version",
                    explanation=(
                        f"Source '{rule.source_document_id}' is an undated FAQ/portal document "
                        "(publication_date=None, effective_from=None) and cannot alone verify a "
                        "version-specific 2023 Operational Guidelines claim."
                    ),
                    requires_abstention=True,
                    is_version_mismatch=False,
                )
            return TemporalResolutionResult(
                is_applicable=False,
                temporal_status="undated_source_temporal_uncertainty",
                explanation=(
                    f"Source '{rule.source_document_id}' has unresolved temporal applicability "
                    "(effective_from=None)."
                ),
                requires_abstention=True,
                is_version_mismatch=False,
            )
        if rule.policy_era == "announcement_2025_dec":
            return TemporalResolutionResult(
                is_applicable=True,
                temporal_status="matched_2025_dec_announcement",
                explanation="Rule matches verified PIB announcement PRID=2197713.",
            )

    # Case 7: PM-KISAN policy versions
    if rule.scheme == "PM_KISAN" or req_ver in ("pmkisan_current", "2019_original_pmkisan"):
        if req_ver in ("pmkisan_current", "2023_guidelines", None):
            if rule.policy_era in ("universal_landholder_2019_onwards", "revised_2020", "official"):
                return TemporalResolutionResult(
                    is_applicable=True,
                    temporal_status="matched_pmkisan_universal_version",
                    explanation="Rule is verified under the active universal landholder PM-KISAN guidelines (2019 onwards).",
                )
            if rule.policy_era == "original_launch_feb2019":
                return TemporalResolutionResult(
                    is_applicable=False,
                    temporal_status="superseded_2019_historical_pmkisan_rule",
                    explanation="Rule is from the superseded Feb 2019 PM-KISAN launch guidelines (capped at 2 ha).",
                    requires_abstention=False,
                    is_version_mismatch=True,
                )
        if req_ver == "2019_original_pmkisan":
            if rule.policy_era == "original_launch_feb2019":
                return TemporalResolutionResult(
                    is_applicable=True,
                    temporal_status="matched_2019_original_pmkisan",
                    explanation="Rule matches the original February 2019 PM-KISAN launch guidelines (2 ha cap).",
                )
            return TemporalResolutionResult(
                is_applicable=False,
                temporal_status="policy_version_mismatch_expected_2019_pmkisan",
                explanation=f"Claim asks for original 2019 guidelines, but rule is from era '{rule.policy_era}'.",
                requires_abstention=False,
                is_version_mismatch=True,
            )

    # Case 8: Historical Indira Awaas Yojana (IAY) vs active PMAY-G
    if rule.policy_era in ("historical_iay", "iay_historical_pre2016") or req_ver == "historical_iay":
        if req_ver == "historical_iay":
            if rule.policy_era in ("historical_iay", "iay_historical_pre2016"):
                return TemporalResolutionResult(
                    is_applicable=True,
                    temporal_status="matched_historical_iay_version",
                    explanation="Rule matches historical Indira Awaas Yojana (IAY) norm.",
                )
            return TemporalResolutionResult(
                is_applicable=False,
                temporal_status="policy_version_mismatch_expected_iay",
                explanation=f"Claim asks for historical IAY norm, but rule is from '{rule.policy_era}'.",
                requires_abstention=False,
                is_version_mismatch=True,
            )
        return TemporalResolutionResult(
            is_applicable=False,
            temporal_status="superseded_historical_iay_rule",
            explanation=(
                "Rule is from the superseded Indira Awaas Yojana (IAY, 20 sq.m prior to 2016) "
                "and cannot establish a current PMAY-G (25 sq.m) claim."
            ),
            requires_abstention=False,
            is_version_mismatch=True,
        )

    # Case 9: Flagship schemes and user-uploaded custom policy documents
    if (
        rule.source_document_id.startswith("DOC_UPLOAD_")
        or rule.policy_era in ("uploaded_active", "mgnrega_act", "pmjay_current", "pmayg_current", "pmkusum_current", "pmmy_current")
    ):
        return TemporalResolutionResult(
            is_applicable=True,
            temporal_status="matched_active_scheme_policy",
            explanation=f"Rule is verified under active policy era '{rule.policy_era}'.",
            requires_abstention=False,
            is_version_mismatch=False,
        )

    return TemporalResolutionResult(
        is_applicable=False,
        temporal_status="unresolved_temporal_scope",
        explanation=f"Could not establish temporal applicability for requested_policy_version='{req_ver}'.",
        requires_abstention=True,
        is_version_mismatch=False,
    )
