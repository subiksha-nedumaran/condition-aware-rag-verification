"""Deterministic rule-based numerical claim parser and schema validator for FieldGuard."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from fieldguard.numeric_normalizer import normalize_claim_numerics

REQUIRED_PARSED_CLAIM_FIELDS: tuple[str, ...] = (
    "scheme",
    "claimed_value",
    "claimed_unit",
    "numeric_operator",
    "crop_category",
    "season",
    "qualification",
    "requested_policy_version",
    "requested_effective_date",
    "parse_status",
    "uncertain_fields",
)


@dataclass
class ParsedClaim:
    """Validated structured representation of a parsed candidate numerical claim."""

    scheme: str | None
    claimed_value: float | None
    claimed_unit: str | None
    numeric_operator: str | None
    crop_category: str | None
    season: str | None
    qualification: str | None
    requested_policy_version: str | None
    requested_effective_date: str | None
    parse_status: str
    uncertain_fields: list[str] = field(default_factory=list)
    rule_parameter: str | None = None
    geography: str | None = None
    basis: str | None = None
    canonical_value: float | None = None
    canonical_unit: str | None = None
    claims_unconditional_flat_rate: bool = False
    is_corrupted_number: bool = False
    raw_question: str = ""
    raw_claim: str = ""
    parser_name: str = "deterministic_rule_parser_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_parsed_claim_schema(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Strict schema validation for ParsedClaim dictionaries (used by both the deterministic
    parser and the optional LLM parser).
    """
    errors: list[str] = []
    for req in REQUIRED_PARSED_CLAIM_FIELDS:
        if req not in data:
            errors.append(f"Missing required field '{req}'")

    if "uncertain_fields" in data and not isinstance(data["uncertain_fields"], list):
        errors.append("Field 'uncertain_fields' must be a list of strings")

    if "parse_status" in data and data["parse_status"] not in (
        "success",
        "partial_uncertain",
        "failed_malformed",
    ):
        errors.append(f"Invalid parse_status '{data.get('parse_status')}'")

    if data.get("claimed_value") is not None and not isinstance(
        data["claimed_value"], (int, float)
    ):
        errors.append("Field 'claimed_value' must be numeric or null")

    return len(errors) == 0, errors


def _detect_scheme(text: str) -> str | None:
    t = text.lower()
    if re.search(r"\bpmfby\b|pradhan\s+mantri\s+fasal\s+bima\s+yojana", t):
        return "PMFBY"
    if re.search(r"\brwbcis\b|restructured\s+weather\s+based\s+crop\s+insurance", t):
        return "RWBCIS"
    if re.search(r"\bpm-?kisan\b|pradhan\s+mantri\s+kisan\s+samman\s+nidhi", t):
        return "PM_KISAN"
    if re.search(r"\bnais\b|national\s+agricultural\s+insurance\s+scheme", t):
        return "NAIS"
    return None


def _detect_rule_parameter(text: str) -> str | None:
    t = text.lower()
    if re.search(r"wild\s+animal\s+attack", t):
        return "wild_animal_addon_state_subsidy_share"
    if re.search(r"compulsory\s+for\s+(?:all\s+)?loanee|mandatory\s+for\s+(?:all\s+)?loanee|loanee\s+farmer\s+compulsory", t):
        return "loanee_enrolment_compulsory_share"
    if re.search(r"opt\s*-?\s*out.*?(?:days|prior|cut-?off)|declaration.*?prior\s+to.*?(?:cut-?off|enrolment)", t):
        return "loanee_opt_out_notice_window"
    if re.search(r"central\s+(?:government\s+)?(?:premium\s+)?subsidy.*?(?:capped|ceiling|limit|up\s+to).*?(?:actuarial|irrigated|unirrigated|rainfed)", t) or re.search(
        r"actuarial\s+(?:premium\s+)?rate\s+(?:ceiling|cap|limit)\s+for\s+central\s+subsidy", t
    ):
        return "central_subsidy_actuarial_cap"
    if re.search(
        r"(?:normal\s+)?premium\s+subsidy.*?(?:shared|sharing|ratio|central\s+share|centre\s+and\s+state)|"
        r"central\s+government(?:'s)?\s+share\s+of\s+(?:the\s+)?(?:normal\s+)?premium\s+subsidy|"
        r"\b50\s*:\s*50\b|\b90\s*:\s*10\b",
        t,
    ):
        return "central_subsidy_share"
    if re.search(r"indemnity\s+level", t):
        return "indemnity_level"
    if re.search(r"threshold\s+yield.*?(?:best\s+\d+\s+years|preceding\s+7\s+years|how\s+many\s+best\s+years|average\s+yield\s+of\s+best)", t):
        return "threshold_yield_best_years"
    if re.search(r"prevented\s+(?:or\s+failed\s+)?sowing|failed\s+sowing", t):
        return "prevented_sowing_on_account_payout"
    if re.search(r"mid-?season\s+adversity", t):
        return "mid_season_adversity_relief"
    if re.search(r"post-?harvest\s+loss", t) and re.search(r"\b(?:days?|weeks?|period|drying|cut-and-spread)\b", t) and not re.search(r"\bhours?\b|intimat", t):
        return "post_harvest_coverage_window"
    if re.search(r"intimat|report.*?(?:localized|calamity|hailstorm|inundation|cloudburst|loss)|within\s+\d+\s+hours", t):
        return "localized_loss_intimation_window"
    if re.search(r"penal\s+interest|interest\s+penalty|late\s+(?:claim\s+)?settlement\s+interest|interest.*?delayed\s+(?:claim|subsidy)", t):
        return "late_settlement_penal_interest"
    if re.search(r"settle\s+claims|claim\s+settlement\s+(?:timeline|window|period).*?(?:after\s+receipt|yield\s+data)", t):
        return "claim_settlement_timeline"
    if re.search(r"upload.*?(?:portal|ncip|proposal)|bank.*?(?:upload|window).*?cut-?off", t):
        return "bank_portal_upload_window"
    if re.search(r"\biec\b|information,\s*education\s+and\s+communication|administrative\s+and\s+iec\s+expense", t):
        return "iec_admin_expense_rate"
    if re.search(r"women\s+(?:cultivators|farmers)\s+outreach|crop\s+cutting\s+experiments|\bcces\b|small/marginal\s+farmers\s+holding|weekly\s+block\s+camp", t):
        # Explicitly check if the claim is trying to assert a farmer premium rate from distractor text
        if re.search(r"farmer\s+premium|maximum\s+(?:insurance\s+charges|premium)", t):
            return "farmer_premium_rate"
        return "unrelated_operational_target"
    if re.search(r"premium|insurance\s+charges", t):
        return "farmer_premium_rate"
    return None


def _detect_season(text: str, rule_param: str | None) -> str | None:
    t = text.lower()
    has_kharif = bool(re.search(r"\bkharif\b", t))
    has_rabi = bool(re.search(r"\brabi\b", t))
    if re.search(r"\bzaid\b|\bsummer\s+season\b", t):
        return "zaid_summer"
    if has_kharif and has_rabi:
        return "annual"
    if has_kharif:
        if rule_param == "farmer_premium_rate" and re.search(
            r"annual\s+commercial|annual\s+horticultural|commercial\s+and\s+horticultural|commercial\s+crops?|horticultural\s+crops?",
            t,
        ) and not re.search(r"betelvine", t):
            return "annual"
        return "kharif"
    if has_rabi:
        if rule_param == "farmer_premium_rate" and re.search(
            r"annual\s+commercial|annual\s+horticultural|commercial\s+and\s+horticultural|commercial\s+crops?|horticultural\s+crops?",
            t,
        ):
            return "annual"
        return "rabi"
    if re.search(r"\bannual\s+commercial|\bannual\s+horticultural", t):
        return "annual"
    if rule_param and rule_param != "farmer_premium_rate":
        return "annual"
    return None


def _detect_crop_category(text: str, rule_param: str | None) -> str | None:
    t = text.lower()
    if re.search(r"\bbetelvine\b", t):
        return "perennial_betelvine_pilot"
    if re.search(r"wild\s+animal\s+attack", t):
        return "wild_animal_attack_addon"
    if re.search(r"\blivestock\b|\bdairy\s+cattle\b|\baquaculture\b|\bshrimp\b|\bpoultry\b|\btractor\b", t):
        return "non_covered_livestock_aquaculture"
    if re.search(
        r"food\s*-?\s*grains?\b|oilseeds?\b|\bcereals?\b|\bmillets?\b|\bpulses\b|\bpaddy\b|\bwheat\b|\bmustard\b|\bsoybean\b|\bgroundnut\b|\bgram\b|\blentil\b|\bsorghum\b|\bbajra\b|\bmaize\b",
        t,
    ):
        return "food_grain_and_oilseed"
    if re.search(
        r"commercial\s+crops?|horticultural\s+crops?|annual\s+commercial|annual\s+horticultural|"
        r"perennial\s+horticultural|\bcotton\b|\bsugarcane\b|\bjute\b|\bpotato\b|\bonion\b|\bbanana\b|\bchilli\b|\bturmeric\b|\bginger\b|\bspices?\b",
        t,
    ):
        return "commercial_and_horticultural"
    if rule_param == "central_subsidy_actuarial_cap":
        if re.search(r"\bunirrigated\b|\brainfed\b|less\s+than\s+50(?:\.0)?%\s+irrigated", t):
            return "unirrigated_crops"
        if re.search(r"\birrigated\b|50(?:\.0)?%\s+or\s+more\s+irrigated", t):
            return "irrigated_crops"
        return None
    if rule_param and rule_param not in ("farmer_premium_rate", "central_subsidy_actuarial_cap"):
        return "all_notified_crops"
    return None


def _detect_geography(text: str, rule_param: str | None) -> str | None:
    t = text.lower()
    if re.search(
        r"north\s*-?\s*eastern\s+(?:region|states?)|\bner\s+states?\b|\bassam\b|\bmeghalaya\b|\btripura\b|\bmanipur\b|\bmizoram\b|\bnagaland\b|\barunachal\b|\bsikkim\b",
        t,
    ):
        return "north_eastern_states"
    if re.search(
        r"general\s+states?|non-?\s*ner\s+states?|plains\s+states?|\bmaharashtra\b|\buttar\s+pradesh\b|\bmadhya\s+pradesh\b|\brajasthan\b|\bpunjab\b|\bharyana\b|\bgujarat\b|\bkarnataka\b",
        t,
    ):
        if rule_param == "central_subsidy_share":
            return "general_states"
        return "all_india"
    if rule_param == "central_subsidy_share":
        return None
    return "all_india"


def _detect_temporal_request(text: str) -> tuple[str | None, str | None]:
    """
    Extract (requested_policy_version, requested_effective_date) from question/claim text.
    Never infers an effective date from a publication date.
    """
    t = text.lower()
    req_date: str | None = None

    # Explicit ISO date or year-season date
    m_iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", t)
    if m_iso:
        req_date = m_iso.group(1)

    if re.search(
        r"2016\s+(?:pmfby\s+)?(?:historical\s+|original\s+|operational\s+)*guidelines|"
        r"(?:historical|original)\s+2016\s+(?:pmfby\s+)?(?:operational\s+)?guidelines|"
        r"pre-?2020\s+guidelines|\bin\s+201[6789]\b|kharif\s+201[6789]",
        t,
    ):
        if req_date is None and re.search(r"\bin\s+2018\b|kharif\s+2018", t):
            req_date = "2018-07-01"
        elif req_date is None and re.search(r"\bin\s+2017\b|kharif\s+2017", t):
            req_date = "2017-07-01"
        return "2016_historical", req_date

    if re.search(
        r"\bcurrently\b|\bcurrent\s+(?:2026\s+)?(?:revised\s+)?(?:pmfby\s+)?policy\b|"
        r"\blatest\s+current\b|\blatest\s+applicable\b|\bas\s+of\s+today\b|\bpresent\s+guidelines\b|"
        r"latest\s+current\s+2026\s+revised",
        t,
    ):
        return "latest_current", req_date

    if re.search(r"2026\s+revised\s+guidelines|2027\s+guidelines|latest\s+2026\s+policy|post-?december\s+2025\s+revised\s+premium", t):
        return "2026_revised_full_unverified", req_date

    if re.search(r"december\s+2025\s+(?:pib\s+|government\s+)?(?:press\s+release|announcement|update|revision)|prid\s*=\s*2197713|12\s+december\s+2025", t):
        if re.search(r"revised\s+december\s+2025\s+(?:full\s+)?operational\s+guidelines\s+premium|new\s+2026\s+premium\s+rate", t):
            return "2025_dec_full_guidelines_unverified", req_date
        return "2025_dec_announcement", req_date

    if re.search(
        r"2023\s+(?:revamped\s+|pmfby\s+|rwbcis\s+|operational\s+|pilot\s+)*(?:guidelines|rules|addendum)|"
        r"revamped\s+operational\s+guidelines\s*\(?2023\)?|2020\s+revamped\s+guidelines",
        t,
    ):
        return "2023_guidelines", req_date

    return "2023_guidelines", req_date


class DeterministicClaimParser:
    """
    Deterministic rule-based parser (Parser A) that extracts a candidate numerical claim
    into the validated ParsedClaim schema, explicitly tracking uncertain or missing fields.
    """

    def __init__(self, preserve_uncertainty: bool = True) -> None:
        self.preserve_uncertainty = preserve_uncertainty

    def parse(self, question: str, candidate_claim: str | None = None) -> ParsedClaim:
        combined = f"{question or ''} {candidate_claim or ''}".strip()
        if not combined:
            return ParsedClaim(
                scheme=None,
                claimed_value=None,
                claimed_unit=None,
                numeric_operator=None,
                crop_category=None,
                season=None,
                qualification=None,
                requested_policy_version=None,
                requested_effective_date=None,
                parse_status="failed_malformed",
                uncertain_fields=[
                    "scheme",
                    "claimed_value",
                    "claimed_unit",
                    "crop_category",
                    "season",
                ],
                raw_question=question or "",
                raw_claim=candidate_claim or "",
            )

        target_text = candidate_claim if (candidate_claim and candidate_claim.strip()) else question
        num_expr = normalize_claim_numerics(target_text)
        # If candidate_claim omitted the number (e.g. "Yes"), fall back to combined text
        if num_expr.primary_value is None:
            num_expr = normalize_claim_numerics(combined)

        scheme = _detect_scheme(combined)
        rule_param = _detect_rule_parameter(combined)
        season = _detect_season(combined, rule_param)
        crop_cat = _detect_crop_category(combined, rule_param)
        geography = _detect_geography(combined, rule_param)
        req_ver, req_date = _detect_temporal_request(combined)

        basis = num_expr.basis or normalize_claim_numerics(combined).basis
        qualifier = num_expr.qualifier or normalize_claim_numerics(combined).qualifier
        claims_uncond = (
            num_expr.claims_unconditional_flat_rate
            or normalize_claim_numerics(combined).claims_unconditional_flat_rate
        )

        # Default basis for standard parameters when not contradicted by an explicit wrong basis
        if basis is None:
            if rule_param in ("farmer_premium_rate", "prevented_sowing_on_account_payout"):
                basis = "sum_insured"
            elif rule_param == "central_subsidy_actuarial_cap":
                basis = "actuarial_premium_rate"
            elif rule_param == "central_subsidy_share":
                basis = "normal_premium_subsidy"
            elif rule_param == "indemnity_level":
                basis = "threshold_yield"
            elif rule_param == "threshold_yield_best_years":
                basis = "preceding_7_years_yield_history"
            elif rule_param == "mid_season_adversity_relief":
                basis = "likely_claims"
            elif rule_param == "post_harvest_coverage_window":
                basis = "post_harvest_drying_period"
            elif rule_param == "localized_loss_intimation_window":
                basis = "time_from_peril_occurrence"
            elif rule_param == "late_settlement_penal_interest":
                basis = "delayed_claim_or_subsidy_amount_per_annum"
            elif rule_param == "claim_settlement_timeline":
                basis = "days_from_receipt_of_yield_data_and_subsidy"
            elif rule_param == "bank_portal_upload_window":
                basis = "days_after_enrolment_cutoff_date"
            elif rule_param == "iec_admin_expense_rate":
                basis = "gross_premium"
            elif rule_param == "loanee_opt_out_notice_window":
                basis = "days_prior_to_enrolment_cutoff_date"
            elif rule_param == "loanee_enrolment_compulsory_share":
                basis = "loanee_farmers_in_notified_area"
            elif rule_param == "wild_animal_addon_state_subsidy_share":
                basis = "wild_animal_addon_cost"

        uncertain: list[str] = []
        if scheme is None:
            uncertain.append("scheme")
        if num_expr.primary_value is None or num_expr.is_corrupted:
            uncertain.append("claimed_value")
        if num_expr.primary_unit is None:
            uncertain.append("claimed_unit")
        if rule_param is None:
            uncertain.append("rule_parameter")
        if rule_param == "farmer_premium_rate":
            if crop_cat is None:
                uncertain.append("crop_category")
            if season is None and crop_cat != "commercial_and_horticultural":
                uncertain.append("season")
        elif rule_param == "central_subsidy_actuarial_cap" and crop_cat is None:
            uncertain.append("crop_category")
        elif rule_param == "central_subsidy_share" and geography is None:
            uncertain.append("geography")

        if num_expr.is_corrupted or num_expr.primary_value is None:
            status = "failed_malformed"
        elif uncertain:
            status = "partial_uncertain"
        else:
            status = "success"

        return ParsedClaim(
            scheme=scheme,
            claimed_value=num_expr.primary_value,
            claimed_unit=num_expr.primary_unit,
            numeric_operator=num_expr.numeric_operator,
            crop_category=crop_cat,
            season=season,
            qualification=qualifier,
            requested_policy_version=req_ver,
            requested_effective_date=req_date,
            parse_status=status,
            uncertain_fields=uncertain,
            rule_parameter=rule_param,
            geography=geography,
            basis=basis,
            canonical_value=num_expr.canonical_value,
            canonical_unit=num_expr.canonical_unit,
            claims_unconditional_flat_rate=claims_uncond,
            is_corrupted_number=num_expr.is_corrupted,
            raw_question=question or "",
            raw_claim=candidate_claim or "",
            parser_name="deterministic_rule_parser_v1",
        )
