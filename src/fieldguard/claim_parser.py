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
    # Generalized multi-scheme condition attributes
    beneficiary_type: str | None = None
    entity_scope: str | None = None
    frequency: str | None = None
    exclusion_category: str | None = None
    loan_category: str | None = None
    period: str | None = None
    distance: str | None = None
    beneficiary_scope: str | None = None
    care_level: str | None = None
    hospitalisation_phase: str | None = None
    claim_scope: str | None = None

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


def _detect_scheme(text: str, default_scheme: str | None = None) -> str | None:
    t = text.lower()
    for pattern, scheme in (
        (r"\bpmay[-_ ]?g\b|awas\s+yojana\s*[-—– ]*\s*gramin|\biay\b|indira\s+awaas", "PMAY_G"),
        (r"\bpm[-_ ]?kusum\b|kisan\s+urja\s+suraksha", "PM_KUSUM"),
        (r"\bpm[-_ ]?jay\b|ayushman|jan\s+arogya\s+yojana", "PM_JAY"),
        (r"\bpmmy\b|\bmudra\b|micro\s+units\s+development", "PMMY"),
        (r"\bmgnreg[as]\b|\bnrega\b|rural\s+employment\s+guarantee", "MGNREGA"),
    ):
        if re.search(pattern, t):
            return scheme
    if re.search(r"\bpmfby\b|pradhan\s+mantri\s+fasal\s+bima\s+yojana", t):
        return "PMFBY"
    if re.search(r"\brwbcis\b|restructured\s+weather\s+based\s+crop\s+insurance", t):
        return "RWBCIS"
    if re.search(r"\bpm-?kisan\b|pradhan\s+mantri\s+kisan\s+samman\s+nidhi", t):
        return "PM_KISAN"
    if re.search(r"\bnais\b|national\s+agricultural\s+insurance\s+scheme", t):
        return "NAIS"

    if default_scheme:
        return default_scheme

    # Domain-keyword fallback when scheme name is omitted
    if re.search(
        r"muster\s+roll|job\s+card|unemployment\s+allowance|"
        r"100\s+days\s+of\s+(?:guaranteed\s+)?(?:wage\s+)?employment|"
        r"gram\s+sabha\s+social\s+audit|worksite\s+cr[eè]che",
        t,
    ):
        return "MGNREGA"
    if re.search(r"\bshishu\b|\bkishore\b|\btarun\s+plus\b|\btarun\b.*?\bloan\b|\bcgfmu\b", t):
        return "PMMY"
    if re.search(
        r"empanelled\s+(?:public\s+or\s+private\s+)?hospitals?|pre-?hospitali[sz]ation|"
        r"post-?hospitali[sz]ation|health\s+benefit\s+packages?|\bhbp\b",
        t,
    ):
        return "PM_JAY"
    if re.search(
        r"standalone\s+solar\s+(?:agriculture\s+)?pumps?|grid-?connected\s+agriculture\s+pumps?|"
        r"solarisation\s+of\s+grid|\bdiscom\b.*?\bpbi\b",
        t,
    ):
        return "PM_KUSUM"
    if re.search(r"pucca\s+house.*?(?:plain|hilly|gramin|swachh\s+bharat)", t):
        return "PMAY_G"
    return None


def _detect_rule_parameter(text: str, scheme: str | None = None) -> str | None:
    t = text.lower()
    scheme = scheme or _detect_scheme(t)
    if scheme == "PMAY_G":
        if re.search(r"floor\s+area|house\s+(?:size|area)|size\s+of\s+(?:the\s+)?house|square\s+met|sq\.?\s*m|\biay\b.*?(?:area|size|sq)", t):
            return "minimum_house_size_sqm"
        if re.search(r"toilet|swachh\s+bharat|\bsbm[-_ ]?g\b|sanitation", t):
            return "toilet_construction_assistance_inr"
        if re.search(r"person-?days|unskilled\s+(?:manual\s+)?(?:labour|wage\s+employment)|mgnrega\s+convergence|\b9[05]\s+(?:person-?)?days", t):
            return "mgnrega_unskilled_labour_person_days"
        if re.search(r"interest\s+subvention", t):
            return "loan_interest_subvention_pct"
        if re.search(r"(?:optional\s+)?(?:institutional\s+|bank\s+|housing\s+)?loan", t):
            return "optional_institutional_loan_cap_inr"
        if re.search(r"state\s+(?:government\s+)?(?:share|funding|contribution|bears?)", t) and not re.search(r"60\s*:\s*40|90\s*:\s*10|central", t):
            return "state_funding_share_pct"
        if re.search(r"central\s+(?:government\s+)?(?:share|funding|contribution|bears?)|funding\s+pattern|shared\s+between|60\s*:\s*40|90\s*:\s*10|100\s*%.*?union\s+territor", t):
            return "central_funding_share_pct"
        if re.search(r"(?:house\s+|construction\s+)completion|complete\s+(?:house\s+)?construction|months?\s+from\s+(?:the\s+)?sanction|completed?\s+within\s+\d+\s+months?", t):
            return "construction_completion_timeline_months"
        if re.search(r"instalments?|geo-?tagged|stages?\s+of\s+construction", t):
            return "minimum_disbursement_instalments_count"
        if re.search(r"\bsc\s*/?\s*st\b|scheduled\s+castes?\s+and\s+scheduled\s+tribes?", t):
            return "sc_st_target_earmarking_pct"
        if re.search(r"minorit(?:y|ies)", t):
            return "minority_target_earmarking_pct"
        if re.search(r"disabilit|\bpwd\b|divyang", t):
            return "pwd_reservation_pct"
        if re.search(r"administrative\s+(?:funds?|expenses?|cost|ceiling|limit)", t):
            return "administrative_funds_ceiling_pct"
        if re.search(r"unit\s+(?:grant\s+)?assistance|financial\s+assistance|grant\s+assistance|housing\s+(?:unit\s+)?grant|\b1,?20,?000\b|\b1,?30,?000\b|\b1\.20?\s*lakh\b|\b1\.30?\s*lakh\b", t):
            return "unit_grant_assistance_inr"
        return None

    if scheme == "PM_JAY":
        if re.search(r"pre-?existing\s+(?:diseases?|conditions?)|waiting\s+period", t):
            return "pre_existing_disease_waiting_period_days"
        if re.search(r"pre-?hospitali[sz]ation|prior\s+to\s+(?:hospital\s+)?admission|before\s+(?:hospital\s+)?admission", t):
            return "pre_hospitalisation_coverage_days"
        if re.search(r"post-?hospitali[sz]ation|after\s+discharge|follow-?up.*?discharge", t):
            return "post_hospitalisation_coverage_days"
        if re.search(r"health\s+benefit\s+packages?|\bhbp\b|procedures?\s+covered|medical\s+and\s+surgical\s+packages?|\b1,?949\b", t):
            return "health_benefit_packages_count"
        if re.search(r"senior\s+citizens?|vay\s+vandana|\b70\s+years\b", t):
            if re.search(r"\brs\.?\b|\brupees?\b|\binr\b|\blakh\b|\bcover\b|\btop-?up\b|\b5,?00,?000\b", t) and not re.search(r"aged?\s+\d+\s+years|minimum\s+age|eligibility\s+age", t):
                return "senior_citizen_topup_cover_inr"
            if re.search(r"aged?|minimum\s+age|eligibility\s+age|\byears\b", t) and not re.search(r"\brs\.?\b|\blakh\b|\b5,?00,?000\b", t):
                return "senior_citizen_age_eligibility_years"
            return "senior_citizen_topup_cover_inr"
        if re.search(r"state\s+(?:government\s+)?(?:share|funding|contribution|bears?)", t) and not re.search(r"central", t):
            return "state_funding_share_pct"
        if re.search(r"central\s+(?:government\s+)?(?:share|funding|contribution|bears?)|premium\s+funding.*?shared|60\s*:\s*40|90\s*:\s*10|union\s+territor.*?100\s*%", t):
            return "central_funding_share_pct"
        if re.search(r"penal\s+interest|delayed\s+(?:hospital\s+)?claim.*?interest|\bper\s+week\b", t):
            return "delayed_claim_penal_interest_weekly_pct"
        if re.search(r"(?:inter-?state|portability).*?(?:claim|settle|turnaround|days)", t):
            return "claim_settlement_turnaround_days_portability"
        if re.search(r"(?:claim\s+settlement|settle\s+(?:hospital\s+)?claims|turnaround\s+time.*?claim)", t):
            return "claim_settlement_turnaround_days"
        if re.search(r"auto-?approv|deemed\s+auto-?approved", t):
            return "pre_authorization_auto_approval_hours"
        if re.search(r"pre-?authori[sz]ation", t):
            return "pre_authorization_turnaround_hours"
        if re.search(r"\bbeds?\b|bed\s+capacity|inpatient\s+bed|empanelment.*?\bbeds?\b", t):
            return "minimum_hospital_beds_general_empanelment"
        if "cashless" in t:
            return "cashless_benefit_percentage"
        if re.search(r"health\s+cover|insurance\s+cover|annual\s+cover|family\s+floater|benefit\s+cover|\b5,?00,?000\b|\b5\s*lakh\b", t):
            return "annual_health_cover_inr"
        return None

    if scheme == "PM_KUSUM":
        if re.search(r"(?:fpo|water\s+user\s+association|\bwua\b|cluster|community\s+irrigation|dark\s+zone).*?(?:\bhp\b|horsepower|capacity|pump)", t):
            return "cluster_community_pump_capacity_hp"
        if re.search(r"\bhp\b|horsepower|pump\s+capacity|capacity\s+of\s+(?:standalone\s+|solar\s+)?pump", t):
            return "max_pump_capacity_hp"
        if re.search(r"(?:national|cumulative|aggregate).*?(?:target|capacity)|10,?000\s*mw", t):
            return "component_a_national_target_mw"
        if re.search(r"sub-?station.*?(?:radius|distance|within|\bkm\b|kilometres?)|\b5\s*(?:km|kilometres?)\b.*?sub-?station", t):
            return "component_a_substation_radius_km"
        if re.search(r"minimum.*?(?:plant\s+capacity|solar\s+power\s+plant)|\b500\s*kw\b", t):
            return "component_a_min_plant_capacity_kw"
        if re.search(r"maximum.*?(?:individual\s+)?(?:plant\s+capacity|solar\s+power\s+plant)|\b2\s*mw\b", t) or (
            re.search(r"component[- ]?a.*?(?:plant\s+capacity|solar\s+power\s+plant)", t) and re.search(r"\bmw\b|megawatts?", t)
        ):
            return "component_a_max_plant_capacity_mw"
        if re.search(r"performance\s+based\s+incentive|\bpbi\b", t):
            if re.search(r"per\s+kwh|per\s+unit|\b0\.40\b|\b40\s+paise\b", t):
                return "discom_pbi_rate_per_kwh_inr"
            if re.search(r"per\s+mw|annual\s+cap|maximum.*?lakh|\b6\.60\s+lakh\b|\b6,?60,?000\b", t):
                return "discom_pbi_annual_cap_per_mw_inr"
            if re.search(r"\byears?\b|duration|period\s+of", t):
                return "discom_pbi_duration_years"
        if re.search(r"solar\s+pv\s+capacity.*?(?:times|multiplier|ratio|pump\s+capacity)|twice\s+the\s+pump\s+capacity", t):
            return "component_c_solar_pv_multiplier"
        if re.search(r"comprehensive\s+maintenance\s+contract|\bcmc\b|after-?sales\s+maintenance", t):
            return "mandatory_vendor_cmc_years"
        if re.search(r"upfront|down-?payment|own\s+margin", t):
            return "farmer_upfront_margin_pct"
        if re.search(r"bank\s+loan|loan\s+component|financed\s+through\s+bank", t):
            return "farmer_bank_loan_share_pct"
        if re.search(r"farmer(?:'s)?\s+(?:share|contribution|bears?|cost)|borne\s+by\s+the\s+farmer", t):
            return "farmer_contribution_pct"
        if re.search(r"state\s+(?:government\s+)?(?:subsidy|share|cfa)", t) and not re.search(r"total|combined|central\s+(?:and|plus|\+)\s+state", t):
            return "state_subsidy_pct"
        if re.search(r"central|\bcfa\b", t) and not re.search(r"total|combined|central\s+(?:and|plus|\+)\s+state", t):
            return "central_subsidy_pct"
        if re.search(r"subsidy|assistance|grant", t) and re.search(r"\b\d+(?:\.\d+)?\s*%|percent|percentage|benchmark\s+cost|tender\s+cost|pump|solar", t):
            return "total_subsidy_pct"
        return None

    if scheme == "PMMY":
        if re.search(r"processing\s+fee", t):
            return "shishu_processing_fee_pct"
        if re.search(r"margin\s+money|promoter\s+contribution", t):
            if "shishu" in t and not re.search(r"kishore|tarun", t):
                return "shishu_margin_money_pct"
            return "kishore_tarun_margin_money_min_pct"
        if re.search(r"collateral|third-?party\s+(?:guarantee|security)|security\s+requirement", t) and not re.search(
            r"(?:shishu|kishore|tarun|maximum\s+loan\s+limit|loans?\s+are\s+sanctioned).*?(?:up\s+to\s+)?(?:rs\.?|inr|₹|\d+\s*lakh)",
            t,
        ):
            return "collateral_security_requirement_pct"
        if re.search(r"interest\s+subvention", t):
            if re.search(r"\bmonths?\b|duration|period", t) and not re.search(r"\b\d+(?:\.\d+)?\s*%\b|\bpercent\b", t):
                return "shishu_interest_subvention_period_months"
            return "shishu_interest_subvention_pct"
        if re.search(r"first-?loss|borne\s+by\s+(?:the\s+)?(?:lending\s+institution|lender|bank|mli)", t):
            return "cgfmu_first_loss_default_borne_by_lender_pct"
        if re.search(r"\bcgfmu\b|credit\s+guarantee|guarantee\s+cover", t):
            return "cgfmu_guarantee_cover_pct"
        if re.search(r"(?:credit\s+corpus|total\s+pmmy|earmark|allocated).*?shishu|shishu.*?(?:corpus|earmark|share\s+of\s+total)", t):
            return "shishu_corpus_earmarking_minimum_pct"
        if re.search(r"extended\s+(?:repayment\s+)?tenure", t):
            return "extended_repayment_tenure_years"
        if re.search(r"repayment\s+tenure|tenure\s+of\s+(?:mudra\s+)?(?:term\s+)?loans?|repaid\s+over", t):
            return "maximum_repayment_tenure_years"
        if re.search(r"minimum\s+(?:eligible\s+|borrower\s+)?age|at\s+least\s+\d+\s+years\s+of\s+age", t):
            return "minimum_borrower_age_years"
        if re.search(r"maximum\s+(?:eligible\s+|borrower\s+)?age|upper\s+age\s+limit", t):
            return "maximum_borrower_age_years"
        if re.search(r"tarun\s+plus", t):
            return "tarun_plus_loan_cap_inr"
        for tier in ("shishu", "kishore", "tarun"):
            if tier in t:
                if re.search(r"minimum\s+loan|starts?\s+above|lower\s+limit|floor", t) and not re.search(r"up\s+to|maximum|cap|limit\s+is", t):
                    return f"{tier}_loan_min_inr"
                return f"{tier}_loan_cap_inr"
        return None

    if scheme == "MGNREGA":
        if re.search(r"delayed\s+wage|delay\s+in\s+(?:payment\s+of\s+)?wages?|compensation.*?(?:unpaid|delay|per\s+day|0\.05)|0\.05\s*%", t):
            return "delayed_wage_compensation_rate_per_day"
        if re.search(r"job\s+card", t):
            return "job_card_issuance_timeline_days"
        if re.search(r"muster\s+roll|(?:wages?|wage\s+payment|payment\s+of\s+wages?).*?(?:paid|disbursed|credited|within\s+\d+\s+days)", t):
            return "wage_payment_timeline_days"
        if re.search(r"(?:work|employment)\s+(?:must\s+be\s+)?(?:allocated|provided|given|offered).*?(?:within|days|application|demand)|within\s+\d+\s+days\s+of\s+(?:application|demanding)|application\s+for\s+work", t):
            return "work_allocation_timeline_days"
        if re.search(r"unemployment\s+allowance", t):
            if re.search(r"after\s+(?:the\s+)?(?:first\s+)?30\s+days|beyond\s+30\s+days|rest\s+of\s+the\s+financial\s+year|subsequent\s+period", t):
                return "unemployment_allowance_rate_after_30_days"
            if re.search(r"first\s+30\s+days|initial\s+30\s+days|\b25\s*%|\bone-fourth\b|rate|percent|%", t):
                return "unemployment_allowance_rate_first_30_days"
            if re.search(r"how\s+many\s+days|initial\s+period", t):
                return "unemployment_allowance_initial_period_days"
            return "unemployment_allowance_rate_first_30_days"
        if re.search(r"\bwomen\b.*?(?:share|participation|beneficiaries|priority|one-third|33\.33|minimum|at\s+least)", t):
            return "women_participation_minimum_share_pct"
        if re.search(r"(?:extra|additional)\s+wage|commuting|transport.*?(?:allowance|wage)|beyond\s+5\s*(?:km|kilometres?).*?(?:%|percent|extra|wage)", t):
            return "distance_commuting_extra_wage_pct"
        if re.search(r"radius|within\s+\d+\s*(?:km|kilometres?)\s+of\s+(?:the\s+)?village|distance\s+from\s+village", t):
            return "work_radius_limit_km"
        if re.search(r"cr[eè]che|child\s*care", t):
            if re.search(r"below\s+\d+\s+years|age\s+limit|years\s+of\s+age", t) and not re.search(r"\b\d+\s+(?:or\s+more\s+)?children\b|how\s+many\s+children", t):
                return "worksite_creche_child_age_limit_years"
            return "worksite_creche_children_threshold"
        if re.search(r"ex-?gratia|accidental\s+death|permanent\s+(?:total\s+)?disability|death\s+or\s+(?:permanent\s+)?disability", t):
            return "ex_gratia_death_disability_compensation_inr"
        if re.search(r"state\s+government.*?(?:share|funding|bears?|cost).*?material", t):
            return "state_material_funding_share_pct"
        if re.search(r"central\s+government.*?(?:share|funding|bears?|cost).*?material|75\s*:\s*25", t):
            return "central_material_funding_share_pct"
        if re.search(r"central\s+government.*?(?:share|funding|bears?|cost).*?unskilled\s+(?:manual\s+)?wages?|100\s*%.*?unskilled\s+(?:manual\s+)?wages?.*?central", t):
            return "central_wage_funding_share_pct"
        if re.search(r"material\s+(?:component|share|cap|limit|expenditure)|skilled\s+and\s+semi-?skilled\s+wages?.*?(?:cap|maximum|share|40)", t):
            return "wage_material_ratio_material_cap_pct"
        if re.search(r"wage\s*[-:\/]\s*material\s+ratio|unskilled\s+wage\s+component|60\s*:\s*40.*?wage", t):
            return "wage_material_ratio_wage_share_pct"
        if re.search(r"administrative\s+(?:expense|cost|expenditure|ceiling|limit|cap)", t):
            return "administrative_expense_ceiling_pct"
        if re.search(r"social\s+audit", t):
            return "social_audit_frequency_months"
        if re.search(r"additional\s+(?:\d+\s+)?days.*?(?:forest\s+rights|\bfra\b|drought|calamity)|above\s+the\s+statutory\s+100\s+days", t):
            return "additional_employment_days_fra_drought"
        if re.search(r"guaranteed.*?(?:days|employment)|days\s+of\s+(?:guaranteed\s+)?(?:wage\s+)?employment|\b100\s+days\b|\b150\s+days\b", t):
            return "guaranteed_employment_days"
        return None
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
    if re.search(r"har\s+khet\s+har\s+fasal|70(?:\.0)?%\s+of\s+cultivable", t):
        return "har_khet_har_fasal_enrolment_target"
    if re.search(r"crop\s+cutting\s+experiments|\bcces\b", t):
        if re.search(r"mandal|revenue\s+circle|\b8\s+cces\b", t):
            return "cce_minimum_per_mandal"
        if re.search(r"gram\s+panchayat|\b4\s+cces\b", t):
            return "cce_minimum_per_gram_panchayat"
    if re.search(r"women\s+(?:cultivators|farmers)\s+outreach|crop\s+cutting\s+experiments|\bcces\b|small/marginal\s+farmers\s+holding|weekly\s+block\s+camp", t):
        # Explicitly check if the claim is trying to assert a farmer premium rate from distractor text
        if re.search(r"farmer\s+premium|maximum\s+(?:insurance\s+charges|premium)", t):
            return "farmer_premium_rate"
        return "unrelated_operational_target"

    # PM-KISAN rule parameters
    if re.search(
        r"research\s+grant|stipend|housing\s+loan|medical\s+(?:insurance\s+)?allowance|"
        r"vehicle\s+allowance|wage\s+supplement|emergency\s+advance\s+grant|scanner\s+subsidy|"
        r"biometric\s+scanner|account\s+opening\s+fee|tractor|power\s+tiller|"
        r"milch\s+(?:dairy\s+)?cows?|poultry\s+shed|artificial\s+insemination|fish\s+pond|"
        r"aquaculture|\burea\b|certified\s+seeds?|drip\s+irrigation|micro-?irrigation|"
        r"bio-?pesticide|interest\s+waiver|tax\s+(?:deduction|rebate)|solar\s+water\s+pumps?|"
        r"warehouse\s+drying|grain\s+storage|harvested\s+grain.*?\bdried\b",
        t,
    ) and (scheme == "PM_KISAN" or re.search(r"pm-?kisan|kisan\s+samman", t)):
        return None
    if re.search(r"state\s+administrative\s+expenses?", t) and (scheme == "PM_KISAN" or "kisan" in t):
        return "admin_expense_share"
    if re.search(r"funds?\s+are\s+allocated.*?food\s+processing", t) and (scheme == "PM_KISAN" or "kisan" in t):
        return "fund_allocation"
    if re.search(r"physical\s+verification|random\s+sample\s+of\s+\d+\s*%|state\s+nodal\s+officers?.*?verif", t):
        return "state_nodal_officer_verification_sample_pct"
    if re.search(
        r"aadhaar\s+payment\s+bridge|\bapbs\b|aadhaar-?seeded\s+bank|100\s*(?:%|percent)\s+electronically|"
        r"transferred.*?electronically.*?(?:aadhaar|apbs)|how\s+are\s+financial\s+benefits\s+delivered.*?bank\s+accounts|"
        r"paid\s+in\s+cash.*?\b(?:percent|%)",
        t,
    ):
        return "aadhaar_seeding_requirement"
    if re.search(r"pensioner.*?threshold|monthly\s+pension.*?(?:rs\.?|inr|\d)|pension\s+is\s+rs\.?\s*\d+|\brs\.?\s*\d[\d,]*\s*(?:or\s+more\s+|or\s+higher\s+)?.*?pension", t):
        return "statutory_exclusion_pension_threshold"
    if re.search(r"months?\s+per\s+instalment|every\s+\d+\s+months|instalment\s+period|how\s+many\s+months.*?instalment", t) and not re.search(
        r"\brs\.?\s*\d|\binr\s*\d|\d+\s*rupees|window\s+and\s+amount|amount\s+disbursed",
        t,
    ):
        return "instalment_period_months"
    if re.search(
        r"instalment\s+amount|per\s+instalment|each\s+(?:four-?monthly\s+)?instalment|"
        r"four-?monthly\s+instalment.*?(?:rs\.?|inr|\d)|(?:first|second|third|1st|2nd|3rd)\s+instalment.*?(?:rs\.?|inr|\d)|"
        r"(?:rs\.?|inr)\s*\d[\d,]*.*?(?:first|second|third)\s+instalment|\b2000\b.*?(?:instalment|installment)",
        t,
    ):
        return "instalment_amount"
    if re.search(r"how\s+many\s+instalments|number\s+of\s+instalments|three\s+equal\s+instalments|\b\d+\s+(?:equal\s+|quarterly\s+|four-?monthly\s+)?instalments\b", t) and not re.search(r"rs\.?\s*6,?000|annual\s+(?:income\s+)?support\s+of\s+rs", t):
        return "instalments_per_year"
    if re.search(r"annual\s+(?:income\s+)?support|per\s+annum|per\s+year|yearly\s+benefit|\b6000\b", t) and (
        re.search(r"pm-?kisan|kisan|income\s+support|farmer\s+fam", t) or not re.search(r"pmfby|premium|crop|bima", t)
    ):
        return "annual_income_support"
    if re.search(
        r"landholding\s+(?:ceiling|limit|cap|eligibility)|(?:maximum|up\s+to|restrict\s+eligibility\s+to)\s+(?:of\s+)?\d+(?:\.\d+)?\s*(?:ha|hectares?)|how\s+many\s+hectares\s+of\s+land",
        t,
    ) and re.search(r"pm-?kisan|kisan|eligibility|2019", t):
        return "landholding_eligibility_cap_ha"
    if re.search(r"\bekyc\b|electronic\s+know\s+your\s+customer", t):
        return "mandatory_ekyc_requirement"
    if re.search(r"exclusion|excluded|statutory\s+exclusion|ineligible|disqualif|all\s+landholding.*?eligible|medium\s+and\s+large.*?qualify", t) and re.search(r"pm-?kisan|kisan", t):
        if re.search(r"all\s+landholding.*?eligible|eligible\s+regardless\s+of\s+land\s+size|medium\s+and\s+large.*?qualify", t):
            return "annual_income_support"
        return "statutory_exclusion"

    if re.search(r"premium|insurance\s+charges", t):
        return "farmer_premium_rate"
    return None


def _detect_beneficiary_type(text: str) -> str | None:
    t = text.lower()
    if re.search(r"urban\s+commercial\s+traders?|commercial\s+traders?", t):
        return "non_agricultural_traders"
    if re.search(r"agricultural\s+trainees?|student\s+trainees?", t):
        return "agricultural_trainees"
    if re.search(r"agricultural\s+universit(?:y|ies)", t):
        return "agricultural_universities"
    if re.search(r"\btenant\b|\btenant\s+farmers?\b|\bsharecroppers?\b", t):
        return "tenant_farmer"
    if re.search(r"\bagricultural\s+labourers?\b|\bagricultural\s+laborers?\b|\blandless\b", t):
        return "agricultural_laborer"
    if re.search(r"small\s+and\s+marginal|smf|\bup\s+to\s+2\s*(?:ha|hectares?)\b", t):
        return "small_and_marginal_farmers"
    if re.search(r"medium\s+and\s+large|\bmore\s+than\s+2\s*(?:ha|hectares?)\b", t):
        return "medium_and_large_farmers"
    if re.search(r"institutional\s+landholders?|corporate\s+agricultural\s+institutions?|institutional\s+farms?", t):
        return "institutional_landholder"
    if re.search(r"constitutional\s+post", t):
        return "constitutional_post_holder"
    if re.search(r"public\s+representatives?|ministers?|members?\s+of\s+parliament|\bmps?\b|\bmlas?\b", t):
        return "public_representative"
    if re.search(r"government\s+employees?|govt\s+employees?|gazetted\s+officers?|government\s+officers?|govt\s+officers?", t):
        return "government_employee"
    if re.search(r"pensioners?|pension", t):
        return "pensioners"
    if re.search(r"income\s+tax\s+payees?|taxpayers?|paid\s+income\s+tax", t):
        return "income_tax_payee"
    if re.search(r"registered\s+professionals?|doctors?|engineers?|lawyers?|chartered\s+accountants?|architects?", t):
        return "registered_professional"
    if re.search(r"all\s+landholding|landholding\s+farmers?|landholder\s+farmers?|cultivable\s+land|all\s+farmers?|eligible\s+farmers?|farmer\s+famil(?:y|ies)", t):
        return "all_landholding_farmers"
    return None


def _detect_exclusion_category(text: str) -> str | None:
    t = text.lower()
    if re.search(r"institutional\s+landholders?|corporate\s+agricultural\s+institutions?|institutional\s+farms?", t):
        return "institutional_landholder"
    if re.search(r"constitutional\s+post", t):
        return "constitutional_post_holder"
    if re.search(r"public\s+representatives?|ministers?|members?\s+of\s+parliament|\bmps?\b|\bmlas?\b", t):
        return "public_representative"
    if re.search(r"income\s+tax\s+payee|paid\s+income\s+tax", t):
        return "income_tax_payee"
    if re.search(r"pensioner|pension\s+of\s+rs\s*10000", t):
        return "pensioner_ge_10000"
    if re.search(r"government\s+employees?|govt\s+employees?|central/state\s+govt|government\s+officers?|govt\s+officers?", t):
        return "government_employee"
    if re.search(r"registered\s+professionals?|doctors?|engineers?|lawyers?|chartered\s+accountants?|architects?", t):
        return "registered_professional"
    return None


def _detect_frequency(text: str) -> str | None:
    t = text.lower()
    if re.search(r"per\s+instalment|each\s+instalment|four-?monthly|(?:first|second|third|1st|2nd|3rd)\s+instalment|instalment\s+window", t):
        return "per_instalment"
    if re.search(r"per\s+annum|per\s+year|annual|yearly|full\s+financial\s+year", t):
        return "annual"
    if re.search(r"monthly|per\s+month", t):
        return "monthly"
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
        if rule_param in (
            "annual_income_support",
            "instalment_amount",
            "instalments_per_year",
            "instalment_period_months",
            "landholding_eligibility_cap_ha",
            "mandatory_ekyc_requirement",
            "statutory_exclusion",
            "statutory_exclusion_pension_threshold",
            "aadhaar_seeding_requirement",
        ):
            return None
        return "all_notified_crops"
    return None


def _detect_geography(text: str, rule_param: str | None, scheme: str | None = None) -> str | None:
    t = text.lower()
    if re.search(r"union\s+territor(?:y|ies)\s+without\s+legislature|\buts?\b\s+without\s+legislature", t):
        return "union_territories_without_legislature"
    if re.search(r"union\s+territor(?:y|ies)|\b(?:in\s+|for\s+)uts?\b", t):
        return "union_territories"
    if scheme == "MGNREGA" and re.search(r"(?<!non-)(?<!non\s)\bdrought\b|\bcalamity\b|\bfra\b|forest\s+rights", t):
        return "drought_or_calamity_notified_areas"
    if re.search(
        r"\b(?:hilly\s+(?:states?|areas?|districts?)|difficult\s+areas?|himalayan\s+states?|"
        r"integrated\s+action\s+plan|\biap\b\s+districts?|uttarakhand|himachal\s+pradesh|jammu\s+and\s+kashmir|ladakh|island\s+uts?)\b",
        t,
    ):
        return "hilly_areas"
    if re.search(r"\b(?:plain\s+areas?|plains\s+areas?|in\s+the\s+plains|plains)\b", t):
        return "plains_areas"
    if re.search(
        r"north\s*-?\s*eastern\s+(?:region|states?)|\bner\s+states?\b|\bne\s+states?\b|\bassam\b|\bmeghalaya\b|\btripura\b|\bmanipur\b|\bmizoram\b|\bnagaland\b|\barunachal\b|\bsikkim\b",
        t,
    ):
        return "north_eastern_states"
    if re.search(
        r"general\s+states?|non-?\s*ner\s+states?|non-?\s*special\s+category|plains\s+states?|\bmaharashtra\b|\buttar\s+pradesh\b|\bmadhya\s+pradesh\b|\brajasthan\b|\bpunjab\b|\bharyana\b|\bgujarat\b|\bkarnataka\b|\bbihar\b|\btamil\s+nadu\b|\bandhra\s+pradesh\b|\btelangana\b|\bodisha\b",
        t,
    ):
        if rule_param == "central_subsidy_share" or scheme in ("PM_JAY", "PMAY_G", "PM_KUSUM"):
            return "general_states"
        return "all_india"
    if rule_param == "central_subsidy_share":
        return None
    return "all_india"


def _detect_temporal_request(text: str, scheme: str | None = None) -> tuple[str | None, str | None]:
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

    if re.search(r"\bindira\s+awaas\s+yojana\b|\biay\b|pre-?2016\s+rural\s+housing", t):
        return "historical_iay", req_date

    if re.search(
        r"2016\s+(?:pmfby\s+)?(?:historical\s+|original\s+|operational\s+)*guidelines|"
        r"(?:historical|original)\s+2016\s+(?:pmfby\s+)?(?:operational\s+)?guidelines|"
        r"pre-?2020\s+guidelines|\bin\s+201[6789]\b|kharif\s+201[6789]",
        t,
    ) and scheme in (None, "PMFBY", "RWBCIS"):
        if req_date is None and re.search(r"\bin\s+2018\b|kharif\s+2018", t):
            req_date = "2018-07-01"
        elif req_date is None and re.search(r"\bin\s+2017\b|kharif\s+2017", t):
            req_date = "2017-07-01"
        return "2016_historical", req_date

    if re.search(r"2028\s+(?:unverified\s+|future\s+)*draft|future\s+draft\s+guidelines", t):
        return "2028_unverified_draft", req_date

    if re.search(r"2026\s+revised\s+guidelines|2027\s+guidelines|latest\s+2026\s+policy|post-?december\s+2025\s+revised\s+premium", t):
        return "2026_revised_full_unverified", req_date

    if scheme in (None, "PMFBY", "RWBCIS") and re.search(
        r"\bcurrently\b|\bcurrent\s+(?:2026\s+)?(?:revised\s+)?(?:pmfby\s+)?policy\b|"
        r"\blatest\s+current\b|\blatest\s+applicable\b|\bas\s+of\s+today\b|\bpresent\s+guidelines\b|"
        r"latest\s+current\s+2026\s+revised",
        t,
    ):
        return "latest_current", req_date

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

    # PM-KISAN policy eras
    if re.search(r"february\s+2019|feb\s+2019|original\s+(?:launch\s+)?guidelines|initial\s+launch\s+era", t) and re.search(r"kisan|pm-?kisan", t):
        return "2019_original_pmkisan", req_date
    if re.search(r"\bpm-?kisan\b|kisan\s+samman\s+nidhi", t):
        if re.search(r"2019\s+(?:launch\s+)?(?:guidelines|rules)", t) and not re.search(r"june|may|revised|expanded|all\s+landholding", t):
            return "2019_original_pmkisan", req_date
        return "pmkisan_current", req_date

    return "2023_guidelines", req_date


class DeterministicClaimParser:
    """
    Deterministic rule-based parser (Parser A) that extracts a candidate numerical claim
    into the validated ParsedClaim schema, explicitly tracking uncertain or missing fields.
    """

    def __init__(self, preserve_uncertainty: bool = True) -> None:
        self.preserve_uncertainty = preserve_uncertainty

    def parse(
        self,
        question: str,
        candidate_claim: str | None = None,
        default_scheme: str | None = None,
    ) -> ParsedClaim:
        combined = f"{question or ''} {candidate_claim or ''}".strip()
        if not combined:
            return ParsedClaim(
                scheme=default_scheme,
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

        scheme = _detect_scheme(combined, default_scheme=default_scheme)
        rule_param = _detect_rule_parameter(combined, scheme=scheme)
        season = _detect_season(combined, rule_param)
        crop_cat = _detect_crop_category(combined, rule_param)
        geography = _detect_geography(combined, rule_param, scheme=scheme)
        req_ver, req_date = _detect_temporal_request(combined, scheme=scheme)

        beneficiary_type = _detect_beneficiary_type(combined)
        exclusion_cat = _detect_exclusion_category(combined)
        freq = _detect_frequency(combined)

        # Promote secondary numeric mention if rule_param expects a specific unit or upper range cap
        if rule_param and num_expr.secondary_mentions:
            from fieldguard.schemes import get_scheme_adapter
            adapter = get_scheme_adapter(scheme) if scheme else None
            expected_unit: str | None = None
            if adapter and hasattr(adapter, "parameters"):
                for p in adapter.parameters:
                    if hasattr(p, "name") and p.name == rule_param and getattr(p, "canonical_unit", None):
                        expected_unit = p.canonical_unit
                        break
            if expected_unit and num_expr.canonical_unit != expected_unit:
                for sec in num_expr.secondary_mentions:
                    if sec.canonical_unit == expected_unit:
                        num_expr.primary_value = sec.value
                        num_expr.primary_unit = sec.unit
                        num_expr.canonical_value = sec.canonical_value
                        num_expr.canonical_unit = sec.canonical_unit
                        break
            elif (
                any(tag in rule_param for tag in ("_cap_", "_max_", "maximum_"))
                and re.search(r"above\s+.*?\b(?:up\s+to|to)\b|between\s+.*?\band\b|from\s+.*?\bto\b", target_text, re.I)
            ):
                same_unit_secs = [
                    s for s in num_expr.secondary_mentions if s.canonical_unit == num_expr.canonical_unit
                ]
                if same_unit_secs and same_unit_secs[-1].canonical_value > (num_expr.canonical_value or 0.0):
                    best_sec = same_unit_secs[-1]
                    num_expr.primary_value = best_sec.value
                    num_expr.primary_unit = best_sec.unit
                    num_expr.canonical_value = best_sec.canonical_value
                    num_expr.canonical_unit = best_sec.canonical_unit

        # Zero-value exclusion or qualitative scheme claims without explicit digits
        if num_expr.primary_value is None:
            if exclusion_cat is not None or re.search(r"\b(?:statutorily\s+excluded|excluded|ineligible|disqualified)\b", combined, re.I):
                if scheme == "PM_KISAN" or "kisan" in combined.lower() or exclusion_cat is not None:
                    from fieldguard.numeric_normalizer import NormalizedNumericExpression
                    num_expr = NormalizedNumericExpression(
                        primary_value=0.0,
                        primary_unit="rupees",
                        canonical_value=0.0,
                        canonical_unit="rupees",
                        numeric_operator="eq",
                        secondary_mentions=[],
                        basis="per_eligible_farmer_family",
                        qualifier=None,
                        claims_unconditional_flat_rate=False,
                        is_corrupted=False,
                    )
                    rule_param = rule_param or "statutory_exclusion"
            elif (scheme == "PM_KISAN" or "kisan" in combined.lower()) and re.search(
                r"all\s+landholding.*?eligible|eligible\s+regardless\s+of\s+land\s+size|medium\s+and\s+large.*?qualify",
                combined,
                re.I,
            ):
                from fieldguard.numeric_normalizer import NormalizedNumericExpression
                num_expr = NormalizedNumericExpression(
                    primary_value=6000.0,
                    primary_unit="rupees",
                    canonical_value=6000.0,
                    canonical_unit="rupees",
                    numeric_operator="eq",
                    secondary_mentions=[],
                    basis="per_eligible_farmer_family",
                    qualifier=None,
                    claims_unconditional_flat_rate=False,
                    is_corrupted=False,
                )
                rule_param = rule_param or "annual_income_support"

        basis = num_expr.basis or normalize_claim_numerics(combined).basis
        qualifier = num_expr.qualifier or normalize_claim_numerics(combined).qualifier
        claims_uncond = (
            num_expr.claims_unconditional_flat_rate
            or normalize_claim_numerics(combined).claims_unconditional_flat_rate
        )

        if scheme not in (None, "PMFBY", "RWBCIS") and basis == "delayed_claim_or_subsidy_amount_per_annum":
            basis = None

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
            # PM-KISAN bases
            elif rule_param == "annual_income_support":
                basis = "per_eligible_farmer_family"
            elif rule_param == "instalment_amount":
                basis = "per_instalment"
            elif rule_param == "instalments_per_year":
                basis = "per_financial_year"
            elif rule_param == "instalment_period_months":
                basis = "per_instalment_window"
            elif rule_param == "landholding_eligibility_cap_ha":
                basis = "combined_cultivable_landholding"
            elif rule_param in ("mandatory_ekyc_requirement", "aadhaar_seeding_requirement"):
                basis = "all_registered_beneficiaries"
            elif rule_param == "statutory_exclusion_pension_threshold":
                basis = "monthly_pension"
            elif rule_param in ("admin_expense_share", "fund_allocation"):
                basis = "scheme_expenditure"

        if scheme == "PM_KISAN":
            if rule_param == "statutory_exclusion_pension_threshold":
                crop_cat = "pensioners"
                beneficiary_type = "pensioners"
                freq = "monthly"
                season = "monthly"
            elif rule_param == "instalment_period_months":
                freq = "per_instalment"
                season = "four_monthly"
            elif rule_param == "instalment_amount":
                if freq is None:
                    freq = "per_instalment"
                season = "four_monthly" if freq == "per_instalment" else freq
            if beneficiary_type in ("non_agricultural_traders", "agricultural_trainees", "agricultural_universities"):
                crop_cat = beneficiary_type
            elif crop_cat is None:
                crop_cat = exclusion_cat or beneficiary_type or "all_landholding_farmers"
            if season is None:
                season = freq or "annual"

        loan_category: str | None = None
        period: str | None = None
        distance: str | None = None
        beneficiary_scope: str | None = None
        care_level: str | None = None
        hospitalisation_phase: str | None = None
        claim_scope: str | None = None

        if scheme in ("MGNREGA", "PM_JAY", "PMAY_G", "PM_KUSUM", "PMMY"):
            # Explicit scheme parameters must not fall through to PMFBY defaults.
            basis = None
            t_comb = combined.lower()
            if scheme == "MGNREGA":
                if re.search(r"\burban\b", target_text, re.I):
                    beneficiary_type = "urban_household"
                elif re.search(r"skilled\s+engineer|contractor|machinery\s+operator", t_comb):
                    beneficiary_type = "skilled_or_contractor_work"
                elif re.search(r"forest\s+rights|\bfra\b|(?<!non-)(?<!non\s)\bdrought\b|\bcalamity\b", t_comb):
                    beneficiary_type = "fra_and_drought_notified_households"
                else:
                    beneficiary_type = "rural_household"
                if re.search(r"after\s+(?:the\s+)?(?:first\s+)?30\s+days|beyond\s+30\s+days|subsequent", t_comb):
                    period = "after_30_days"
                elif re.search(r"first\s+30\s+days|initial\s+30\s+days", t_comb):
                    period = "first_30_days"
                if re.search(r"within\s+5\s*(?:km|kilometres?)", t_comb) and not re.search(r"beyond\s+5\s*(?:km|kilometres?)", t_comb):
                    distance = "within_5_km"
                elif re.search(r"beyond\s+5\s*(?:km|kilometres?)", t_comb):
                    distance = "beyond_5_km"
            elif scheme == "PM_JAY":
                beneficiary_type = "eligible_families"
                if re.search(r"per\s+individual\s+member|each\s+individual\s+member|per\s+person", t_comb) and not re.search(r"per\s+family|family\s+floater", t_comb):
                    beneficiary_scope = "per_individual"
                if re.search(r"outpatient|\bopd\b\s+only|standalone\s+opd|routine\s+outpatient", t_comb):
                    care_level = "outpatient_opd_only"
                if re.search(r"pre-?hospitali[sz]ation|prior\s+to\s+(?:hospital\s+)?admission|before\s+(?:hospital\s+)?admission", t_comb):
                    hospitalisation_phase = "pre_hospitalisation"
                elif re.search(r"post-?hospitali[sz]ation|after\s+discharge", t_comb):
                    hospitalisation_phase = "post_hospitalisation"
                if re.search(r"inter-?state|portability|outside\s+home\s+state", t_comb):
                    claim_scope = "portability"
                elif re.search(r"intra-?state|within\s+the\s+same\s+state|within\s+state", t_comb):
                    claim_scope = "intrastate"
            elif scheme == "PMMY":
                if re.search(r"tarun\s+plus", t_comb):
                    loan_category = "tarun_plus"
                elif "shishu" in t_comb:
                    loan_category = "shishu"
                elif "kishore" in t_comb:
                    loan_category = "kishore"
                elif "tarun" in t_comb:
                    loan_category = "tarun"
                if re.search(r"corporate\s+compan|large\s+corporate|listed\s+corporate", t_comb):
                    beneficiary_type = "corporate_company"
                elif re.search(r"first-?time\s+(?:new\s+)?borrower|new\s+borrower\s+without\s+prior", t_comb):
                    beneficiary_type = "first_time_new_borrower"
                elif loan_category:
                    beneficiary_type = f"{loan_category}_borrowers"
                else:
                    beneficiary_type = "micro_enterprise_borrowers"
            elif scheme == "PMAY_G":
                if re.search(r"\burban\b", target_text, re.I):
                    beneficiary_type = "urban_household"
                elif re.search(r"\bsc\s*/?\s*st\b|scheduled\s+castes?\s+and\s+scheduled\s+tribes?", t_comb):
                    beneficiary_type = "sc_st_households"
                elif re.search(r"minorit(?:y|ies)", t_comb):
                    beneficiary_type = "minority_households"
                elif re.search(r"disabilit|\bpwd\b|divyang", t_comb):
                    beneficiary_type = "persons_with_disabilities"
                else:
                    beneficiary_type = "rural_beneficiary"
                if geography == "hilly_areas":
                    geography = "hilly_and_difficult_areas"
            elif scheme == "PM_KUSUM":
                if re.search(
                    r"commercial\s+industrial\s+corporat|private\s+industrial\s+park|urban\s+industrial|industrial\s+(?:plant|factor)",
                    t_comb,
                ):
                    beneficiary_type = "commercial_industrial_corporations"
                elif re.search(r"\bfpos?\b|water\s+user\s+association|\bwuas?\b|cluster\s+irrigation|community\s+irrigation", t_comb):
                    beneficiary_type = "fpo_water_user_associations"
                else:
                    beneficiary_type = "individual_farmers"
            crop_cat = beneficiary_type
            season = period or "annual"

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
        elif scheme == "PM_KISAN":
            if rule_param in ("annual_income_support", "instalment_amount") and beneficiary_type is None and crop_cat is None:
                uncertain.append("beneficiary_type")
            elif rule_param == "statutory_exclusion" and exclusion_cat is None and beneficiary_type is None:
                uncertain.append("exclusion_category")

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
            beneficiary_type=beneficiary_type,
            entity_scope=beneficiary_type or crop_cat,
            frequency=freq,
            exclusion_category=exclusion_cat,
            loan_category=loan_category,
            period=period,
            distance=distance,
            beneficiary_scope=beneficiary_scope,
            care_level=care_level,
            hospitalisation_phase=hospitalisation_phase,
            claim_scope=claim_scope,
        )
