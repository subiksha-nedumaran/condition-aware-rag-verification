"""Deterministic numerical, unit, denominator/basis, operator, and qualification normalizer."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any


WORD_TO_NUMBER: dict[str, float] = {
    "zero": 0.0,
    "half": 0.5,
    "one": 1.0,
    "one and a half": 1.5,
    "one point five": 1.5,
    "two": 2.0,
    "two point zero": 2.0,
    "two point five": 2.5,
    "three": 3.0,
    "three point five": 3.5,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "five point zero": 5.0,
    "seven": 7.0,
    "eight": 8.0,
    "ten": 10.0,
    "twelve": 12.0,
    "fourteen": 14.0,
    "fifteen": 15.0,
    "sixteen": 16.0,
    "eighteen": 18.0,
    "twenty": 20.0,
    "twenty-one": 21.0,
    "twenty one": 21.0,
    "twenty-four": 24.0,
    "twenty four": 24.0,
    "twenty-five": 25.0,
    "twenty five": 25.0,
    "thirty": 30.0,
    "forty": 40.0,
    "fifty": 50.0,
    "sixty": 60.0,
    "seventy": 70.0,
    "seventy-two": 72.0,
    "seventy two": 72.0,
    "seventy-five": 75.0,
    "seventy five": 75.0,
    "eighty": 80.0,
    "ninety": 90.0,
    "ninety-five": 95.0,
    "ninety five": 95.0,
    "hundred": 100.0,
    "one hundred": 100.0,
    "one hundred and fifty": 150.0,
    "two thousand": 2000.0,
    "six thousand": 6000.0,
    "ten thousand": 10000.0,
    "twelve thousand": 12000.0,
    "twenty-five thousand": 25000.0,
    "twenty five thousand": 25000.0,
    "fifty thousand": 50000.0,
    "one lakh": 100000.0,
    "five lakh": 500000.0,
    "five lakhs": 500000.0,
    "ten lakh": 1000000.0,
    "ten lakhs": 1000000.0,
    "twenty lakh": 2000000.0,
    "twenty lakhs": 2000000.0,
}


@dataclass
class NormalizedNumericMention:
    """A single normalized numerical mention extracted from text."""

    raw_text: str
    value: float
    unit: str
    canonical_value: float
    canonical_unit: str
    basis: str | None = None
    operator: str = "eq"
    is_corrupted: bool = False
    corruption_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedNumericExpression:
    """Complete normalized numerical representation of a claim or rule."""

    primary_value: float | None
    primary_unit: str | None
    canonical_value: float | None
    canonical_unit: str | None
    basis: str | None
    numeric_operator: str
    qualifier: str | None
    claims_unconditional_flat_rate: bool
    secondary_mentions: list[NormalizedNumericMention] = field(default_factory=list)
    is_corrupted: bool = False
    corruption_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["secondary_mentions"] = [m.to_dict() for m in self.secondary_mentions]
        return d


def detect_numeric_corruption(text: str) -> tuple[bool, str | None]:
    """Detect corrupted percentage or numeric tokens (e.g. '2 . 0 %', '?%', 'NaN%')."""
    if re.search(r"\b\d+\s+\.\s+\d+\s*(?:%|percent|per\s+cent)", text, flags=re.IGNORECASE):
        return True, "Corrupted decimal spacing in percentage token"
    if re.search(r"(?:\?|NaN|null)\s*(?:%|percent|per\s+cent)", text, flags=re.IGNORECASE):
        return True, "Missing or corrupted digits before percentage unit"
    if re.search(r"\b\d+\.\.\d+\s*%", text):
        return True, "Double decimal point in percentage token"
    return False, None


def normalize_unit_and_value(value: float, raw_unit: str) -> tuple[float, str, float, str]:
    """
    Normalize a (value, raw_unit) pair into (normalized_value, normalized_unit,
    canonical_value, canonical_unit).
    Notably:
      - '2 weeks' -> canonical (14.0, 'days')
      - '3 days' (when compared with hours) -> also supports hour/day conversion in comparison
      - '2%' -> (2.0, 'percent', 2.0, 'percent'). Never equates 2% with 0.02%!
    """
    u = (raw_unit or "").strip().lower()
    if u in ("%", "percent", "per cent", "pct", "percentage"):
        return float(value), "percent", float(value), "percent"
    if u in ("week", "weeks", "wk", "wks"):
        return float(value), "weeks", float(value) * 7.0, "days"
    if u in ("day", "days"):
        return float(value), "days", float(value), "days"
    if re.fullmatch(r"(?:person[\s_-]*days?|man[\s_-]*days?|mandays?)", u):
        return float(value), "person_days", float(value), "days"
    if u in ("hour", "hours", "hr", "hrs"):
        return float(value), "hours", float(value), "hours"
    if u in ("year", "years", "yr", "yrs"):
        return float(value), "years", float(value), "years"
    if u in ("hectare", "hectares", "ha"):
        return float(value), "hectares", float(value), "hectares"
    if u in ("acre", "acres"):
        return float(value), "acres", float(value), "acres"
    if u in ("cce", "cces", "experiments"):
        return float(value), "cces", float(value), "cces"
    if u in ("ratio", "share"):
        return float(value), "percent", float(value), "percent"
    if u in ("rupee", "rupees", "rs", "rs.", "inr", "₹"):
        return float(value), "rupees", float(value), "rupees"
    if u in ("month", "months", "mo", "mos"):
        return float(value), "months", float(value), "months"
    if u in ("instalment", "instalments", "installment", "installments"):
        return float(value), "instalments", float(value), "instalments"
    if re.fullmatch(r"(?:sq\.?\s*(?:metres?|meters?|m)|square\s+(?:metres?|meters?)|sqm|m²|m2)", u):
        return float(value), "square_metres", float(value), "square_metres"
    if u in ("hp", "horsepower", "horse power"):
        return float(value), "horsepower", float(value), "horsepower"
    if u in ("km", "kms", "kilometre", "kilometres", "kilometer", "kilometers"):
        return float(value), "kilometres", float(value), "kilometres"
    if u in ("mw", "megawatt", "megawatts"):
        return float(value), "megawatts", float(value), "megawatts"
    if u in ("kw", "kilowatt", "kilowatts"):
        return float(value), "kilowatts", float(value), "kilowatts"
    if u in ("kwh", "kw-h", "kilowatt-hour", "kilowatt-hours"):
        return float(value), "kwh", float(value), "kwh"
    if u in ("bed", "beds"):
        return float(value), "beds", float(value), "beds"
    if u in ("child", "children"):
        return float(value), "children", float(value), "children"
    if u in ("package", "packages", "procedure", "procedures"):
        return float(value), "packages", float(value), "packages"
    if u in ("farmer", "farmers", "beneficiary", "beneficiaries"):
        return float(value), "farmers", float(value), "farmers"
    if u in ("tonne", "tonnes", "metric tonne", "metric tonnes", "mt"):
        return float(value), "tonnes", float(value), "tonnes"
    if u in ("quintal", "quintals", "qtl", "qtls"):
        return float(value), "quintals", float(value), "quintals"
    if u in ("kg", "kgs", "kilogram", "kilograms"):
        return float(value), "kilograms", float(value), "kilograms"
    if u in ("litre", "litres", "liter", "liters"):
        return float(value), "litres", float(value), "litres"
    if u in ("drone", "drones"):
        return float(value), "drones", float(value), "drones"
    if u in ("sapling", "saplings", "tree", "trees"):
        return float(value), "saplings", float(value), "saplings"
    if u in ("cattle", "animal", "animals", "milch animal", "milch animals"):
        return float(value), "animals", float(value), "animals"
    return float(value), u or "dimensionless", float(value), u or "dimensionless"


def extract_basis_from_text(text: str) -> str | None:
    """
    Extract the denominator / basis of a percentage or numerical rule.
    Crucial: 'sum_insured' vs 'actuarial_premium_rate' vs 'threshold_yield' vs
    'likely_claims' vs 'gross_premium' vs 'normal_premium_subsidy' are strictly distinct.
    """
    t = text.lower()

    # Check explicit basis phrases in priority order
    if re.search(r"\b(?:of\s+(?:the\s+)?|on\s+(?:the\s+)?|basis\s+of\s+)?sum\s+insured\b|\b%\s*of\s*si\b|\bof\s+si\b", t):
        # Check if 'actuarial premium rate' is actually the primary subject (e.g. central subsidy cap up to 30% actuarial rate)
        if re.search(r"central\s+(?:government\s+)?(?:premium\s+)?subsidy.*?(?:capped|ceiling|up\s+to).*?actuarial", t) or re.search(
            r"actuarial\s+(?:premium\s+)?rate\s+(?:ceiling|cap|limit|up\s+to)", t
        ):
            return "actuarial_premium_rate"
        return "sum_insured"

    if re.search(r"\bof\s+(?:the\s+)?threshold\s+yield\b|\b%\s*of\s*ty\b|\bindemnity\s+level", t):
        return "threshold_yield"

    if re.search(r"\bof\s+(?:the\s+)?likely\s+claims\b|\bof\s+estimated\s+claims\b", t):
        return "likely_claims"

    if re.search(r"\bof\s+(?:the\s+)?gross\s+premium\b", t):
        return "gross_premium"

    if re.search(r"\bof\s+(?:the\s+)?market\s+value\b|\bof\s+crop\s+market\s+price\b", t):
        return "market_value"

    if re.search(r"\bof\s+(?:the\s+)?input\s+cost\b|\bof\s+cost\s+of\s+cultivation\b", t):
        return "cost_of_cultivation"

    if re.search(r"\bof\s+(?:the\s+)?loan\s+amount\b", t):
        return "loan_amount"

    if re.search(r"actuarial\s+(?:premium\s+)?rate", t) and re.search(r"subsidy\s+(?:cap|ceiling|limit|up\s+to)", t):
        return "actuarial_premium_rate"

    if re.search(r"(?:normal\s+)?premium\s+subsidy\s+shar|\bcentre\s+and\s+state\b|\bcentral\s+(?:government\s+)?share\b|\b50:50\b|\b90:10\b", t):
        if "wild animal" in t:
            return "wild_animal_addon_cost"
        return "normal_premium_subsidy"

    if re.search(r"wild\s+animal\s+attack", t):
        return "wild_animal_addon_cost"

    if re.search(r"per\s+annum|interest.*?delay|penal\s+interest|late\s+(?:settlement|penalty)", t):
        return "delayed_claim_or_subsidy_amount_per_annum"

    if re.search(r"from\s+(?:actual\s+date\s+of\s+)?harvesting|after\s+harvest|post-harvest\s+loss", t):
        return "post_harvest_drying_period"

    if re.search(r"intimat|report.*?(?:localized|calamity|hailstorm|inundation|loss)|from\s+occurrence", t):
        return "time_from_peril_occurrence"

    if re.search(r"settle.*?\bclaims?\b|after\s+receipt\s+of\s+(?:both\s+)?(?:final\s+)?yield\s+data", t):
        return "days_from_receipt_of_yield_data_and_subsidy"

    if re.search(r"upload.*?(?:portal|ncip)|after\s+(?:enrolment\s+)?cut-?off\s+date", t):
        return "days_after_enrolment_cutoff_date"

    if re.search(r"opt\s*-?\s*out|prior\s+to\s+(?:the\s+)?(?:enrolment\s+)?cut-?off", t):
        return "days_prior_to_enrolment_cutoff_date"

    if re.search(r"best\s+\d+\s+(?:years?\s+)?out\s+of\s+(?:preceding|last)\s+7\s+years", t):
        return "preceding_7_years_yield_history"

    if re.search(r"compulsory\s+for\s+(?:all\s+)?loanee|mandatory\s+for\s+(?:all\s+)?loanee", t):
        return "loanee_farmers_in_notified_area"

    return None


def extract_numeric_operator(text: str) -> tuple[str, bool]:
    """
    Determine the comparison operator ('le', 'ge', 'lt', 'gt', 'eq') and whether
    the text asserts an unconditional flat/exact rate that violates a 'whichever is less' cap.
    """
    t = text.lower()

    # Check if the text explicitly asserts an unconditional / flat / always-equal rate
    # e.g., "always pays a fixed 2%", "regardless of whether the actuarial rate is lower",
    # "even if the actuarial rate is 1%", "or actuarial rate whichever is higher"
    claims_unconditional = False
    if re.search(
        r"\b(?:always\s+pays?\s+(?:exactly|a\s+flat|a\s+fixed)|regardless\s+of\s+(?:the\s+)?actuarial|"
        r"even\s+(?:if|when)\s+(?:the\s+)?actuarial\s+rate\s+is\s+(?:lower|less|1%|1\.0%|1\.2%)|"
        r"whichever\s+is\s+(?:higher|more|greater)|irrespective\s+of\s+actuarial|"
        r"without\s+any\s+actuarial\s+rate\s+condition|strictly\s+fixed\s+at\s+\d+(?:\.\d+)?%\s+even\s+when)\b",
        t,
    ):
        claims_unconditional = True

    if re.search(r"\b(?:maximum|at\s+most|up\s+to|capped\s+at|not\s+exceeding|not\s+later\s+than|ceiling\s+of|whichever\s+is\s+(?:less|lower)|within|prevented\s+sowing\s+payout)\b|<=|≤", t):
        return "le", claims_unconditional
    if re.search(r"\b(?:minimum|at\s+least|no\s+less\s+than|not\s+less\s+than|whichever\s+is\s+(?:higher|more|greater))\b|>=|≥", t):
        return "ge", claims_unconditional
    if re.search(r"\b(?:less\s+than|strictly\s+less\s+than|below)\b|\bunder\s+(?:\d|₹|one|two|three|four|five)|<", t):
        return "lt", claims_unconditional
    if re.search(r"\b(?:more\s+than|greater\s+than|exceeding|above)\b|>", t):
        return "gt", claims_unconditional
    return "eq", claims_unconditional


def extract_qualifier_from_text(text: str) -> str | None:
    """Extract normalized qualification status from a claim or evidence string."""
    t = text.lower()
    if re.search(r"whichever\s+is\s+(?:higher|more|greater)", t):
        return "contradictory_whichever_is_higher"
    if re.search(
        r"regardless\s+of\s+(?:the\s+)?actuarial|even\s+(?:if|when)\s+(?:the\s+)?actuarial\s+rate\s+is\s+(?:lower|less|1%|1\.0%|1\.2%)|"
        r"always\s+pays?\s+(?:exactly|a\s+flat|a\s+fixed)|irrespective\s+of\s+actuarial",
        t,
    ):
        return "contradictory_unconditional_flat_rate"
    if re.search(r"actuarial\s+rate.*?whichever\s+is\s+less|whichever\s+is\s+(?:less|lower)", t):
        return "or_actuarial_rate_whichever_is_less"
    if re.search(r"more\s+than\s+75(?:\.0)?%\s*(?:of\s+)?(?:sown\s+|notified\s+)?area.*?(?:prevented|unsown|failed)", t):
        return "when_more_than_75_percent_area_is_prevented_from_sowing"
    if re.search(r"less\s+than\s+25(?:\.0)?%\s*(?:of\s+)?(?:sown\s+|notified\s+)?area.*?(?:prevented|unsown)", t):
        return "contradictory_prevented_sowing_threshold"
    if re.search(r"expected\s+yield.*?(?:falls\s+)?below\s+50(?:\.0)?%", t):
        return "when_expected_yield_falls_below_50_percent_of_threshold_yield"
    if re.search(r"cut\s*-?\s*and\s*-?\s*spread", t):
        return "cut_and_spread_condition_in_field_after_harvesting"
    if re.search(r"stored\s+in\s+(?:warehouse|cold\s+storage|godown)", t):
        return "contradictory_warehouse_storage_post_harvest"
    if re.search(r"100(?:\.0)?%\s*(?:at\s+the\s+cost\s+of|borne\s+by)\s+(?:the\s+)?(?:respective\s+)?state", t):
        return "borne_100_percent_by_state_government_as_optional_addon"
    if re.search(r"100(?:\.0)?%\s*(?:at\s+the\s+cost\s+of|borne\s+by)\s+(?:the\s+)?central\s+government", t):
        return "contradictory_borne_by_central_government"
    return None


def _is_valid_comma_number(number: str) -> bool:
    if "," not in number:
        return True
    return bool(re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d+)?", number))


def extract_all_numeric_mentions(text: str) -> list[NormalizedNumericMention]:
    """
    Extract all numerical mentions from a sentence, preserving order and distinguishing
    percentages, ratios (50:50, 90:10, 60:40, 75:25), days, weeks, hours, years, hectares,
    square metres, horsepower, kilometres, megawatts, kilowatts, beds, children, and packages.
    Never equates 2% with 0.02%.
    """
    mentions: list[NormalizedNumericMention] = []
    t = text

    # 1. Ratios like 50:50, 90:10, 60:40, 75:25
    for m_ratio in re.finditer(r"\b(\d{1,3})\s*:\s*(\d{1,3})\b", t):
        first_val = float(m_ratio.group(1))
        second_val = float(m_ratio.group(2))
        if abs((first_val + second_val) - 100.0) < 1e-6:
            mentions.append(
                NormalizedNumericMention(
                    raw_text=m_ratio.group(0),
                    value=first_val,
                    unit="percent",
                    canonical_value=first_val,
                    canonical_unit="percent",
                )
            )
            if abs(first_val - second_val) > 1e-6:
                mentions.append(
                    NormalizedNumericMention(
                        raw_text=m_ratio.group(0),
                        value=second_val,
                        unit="percent",
                        canonical_value=second_val,
                        canonical_unit="percent",
                    )
                )

    matched_spans: list[tuple[int, int]] = []

    # 2. Prefix currency: e.g. Rs 6000, Rs. 2000, ₹6000, INR 6000, Rs 1,20,000, Rs 5 lakh
    for m_curr in re.finditer(
        r"(?<!\w)(?:rs\.?|inr|₹)\s*(\d(?:[\d,]*\d)?(?:\.\d+)?)(?:\s*(lakh|lakhs|crore|crores|thousand))?(?!\w|,\d)",
        t,
        flags=re.IGNORECASE,
    ):
        number = m_curr.group(1)
        if not _is_valid_comma_number(number):
            continue
        scale = {
            "lakh": 100000,
            "lakhs": 100000,
            "crore": 10000000,
            "crores": 10000000,
            "thousand": 1000,
        }.get((m_curr.group(2) or "").lower(), 1)
        raw_num = float(number.replace(",", "")) * scale
        matched_spans.append(m_curr.span())
        mentions.append(
            NormalizedNumericMention(
                raw_text=m_curr.group(0),
                value=raw_num,
                unit="rupees",
                canonical_value=raw_num,
                canonical_unit="rupees",
            )
        )

    # 3. Explicit numbers with units: e.g. 2.0%, 2%, 0.02%, 14 days, 90 person-days, 2 weeks, 72 hours,
    # 5 years, 2.0 hectares, 6000 rupees, 1,20,000 rupees, 5 lakh rupees, 4 months, 5 km, 2 MW, 500 kW, 10 beds
    # Exclude 4-digit years like 2016, 2020, 2023, 2025, 2026 and helpline 14447 or PRID 2197713
    pattern = re.compile(
        r"(?<![\w.,])(\d(?:[\d,]*\d)?(?:\.\d+)?)\s*"
        r"(?:(lakh|lakhs|crore|crores|thousand)\s+)?"
        r"(?:(?:equal|quarterly|four-monthly|unskilled|medical|surgical|health\s+benefit|inpatient)\s+)?"
        r"(%|(?:square\s+(?:metres?|meters?)|sq\.?\s*(?:metres?|meters?|m)|sqm|m²|m2|"
        r"person[\s_-]*days?|man[\s_-]*days?|mandays?|"
        r"hp|horsepower|horse\s+power|percent|per\s+cent|pct|weeks?|days?|hours?|hrs?|years?|yrs?|"
        r"hectares?|ha|acres?|cces?|rupees?|rs\.?|inr|₹|months?|instalments?|installments?|"
        r"kilometres?|kilometers?|kms?|km|megawatts?|mw|kilowatts?|kw|kwh|kw-h|"
        r"beds?|children|child|packages?|procedures?|farmers?|"
        r"metric\s+tonnes?|tonnes?|quintals?|qtls?|kilograms?|kgs?|kg|litres?|liters?|"
        r"drones?|saplings?|cattle|milch\s+animals?)\b)",
        flags=re.IGNORECASE,
    )
    for m in pattern.finditer(t):
        span = m.span()
        if any(s[0] <= span[0] < s[1] or s[0] < span[1] <= s[1] for s in matched_spans):
            continue
        num_str = m.group(1)
        if not _is_valid_comma_number(num_str):
            continue
        scale_word = (m.group(2) or "").lower()
        scale = {
            "lakh": 100000.0,
            "lakhs": 100000.0,
            "crore": 10000000.0,
            "crores": 10000000.0,
            "thousand": 1000.0,
        }.get(scale_word, 1.0)
        raw_num = float(num_str.replace(",", "")) * scale
        raw_u = m.group(3)
        val, norm_u, can_val, can_u = normalize_unit_and_value(raw_num, raw_u)
        matched_spans.append(span)
        mentions.append(
            NormalizedNumericMention(
                raw_text=m.group(0),
                value=val,
                unit=norm_u,
                canonical_value=can_val,
                canonical_unit=can_u,
            )
        )

    # 3b. Standalone counts / dimensionless items (e.g. 3 subsidized solar water pumps, 2 times the pump capacity)
    dim_pattern = re.compile(
        r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:subsidized\s+)?(?:solar\s+)?(?:water\s+)?(pumps?|times\s+(?:the\s+)?pump\s+capacity)\b",
        flags=re.IGNORECASE,
    )
    for m in dim_pattern.finditer(t):
        span = m.span()
        if any(s[0] <= span[0] < s[1] or s[0] < span[1] <= s[1] for s in matched_spans):
            continue
        raw_num = float(m.group(1))
        matched_spans.append(span)
        mentions.append(
            NormalizedNumericMention(
                raw_text=m.group(0),
                value=raw_num,
                unit="dimensionless",
                canonical_value=raw_num,
                canonical_unit="dimensionless",
            )
        )

    # 4. Spelled-out word numbers followed by unit: e.g. "two percent", "five percent", "two weeks", "three days", "six thousand rupees"
    t_lower = t.lower()
    for word_str, num_val in sorted(WORD_TO_NUMBER.items(), key=lambda kv: -len(kv[0])):
        w_pat = re.compile(
            rf"\b{re.escape(word_str)}\s+(?:(?:equal|quarterly|four-monthly)\s+)?(percent|per\s+cent|weeks?|days?|hours?|years?|rupees?|months?|instalments?|installments?|kilometres?|kilometers?|km|beds?|children|hectares?|acres?)\b",
            flags=re.IGNORECASE,
        )
        for wm in w_pat.finditer(t_lower):
            if any(start < wm.end() and wm.start() < end for start, end in matched_spans):
                continue
            matched_spans.append(wm.span())
            raw_u = wm.group(1)
            val, norm_u, can_val, can_u = normalize_unit_and_value(num_val, raw_u)
            mentions.append(
                NormalizedNumericMention(
                    raw_text=wm.group(0),
                    value=val,
                    unit=norm_u,
                    canonical_value=can_val,
                    canonical_unit=can_u,
                )
            )

    # 5. Fractional word expressions like "one-third of beneficiaries", "one-fourth of the wage rate", "one-half of the wage rate"
    frac_map = {
        "one-third": 33.33,
        "one third": 33.33,
        "one-fourth": 25.0,
        "one fourth": 25.0,
        "one-half": 50.0,
        "one half": 50.0,
    }
    for f_str, f_val in frac_map.items():
        f_pat = re.compile(
            rf"\b{re.escape(f_str)}\b(?:\s*\(\s*\d+(?:\.\d+)?\s*(?:%|percent)\s*\))?\s+of\s+(?:the\s+)?(?:beneficiaries|wages?|wage\s+rate|workers?)",
            flags=re.IGNORECASE,
        )
        for fm in f_pat.finditer(t_lower):
            if any(start < fm.end() and fm.start() < end for start, end in matched_spans):
                continue
            matched_spans.append(fm.span())
            mentions.append(
                NormalizedNumericMention(
                    raw_text=fm.group(0),
                    value=f_val,
                    unit="percent",
                    canonical_value=f_val,
                    canonical_unit="percent",
                )
            )

    return mentions


def normalize_claim_numerics(text: str) -> NormalizedNumericExpression:
    """
    Parse and normalize a candidate claim or question text into a NormalizedNumericExpression.
    When multiple numbers appear in one sentence (e.g. a trigger threshold "more than 75% unsown area"
    and a payout claim "25% of Sum Insured", or a year "2023 guidelines" and a rate "2%"),
    identifies the primary claimed rule value and preserves secondary condition mentions.
    """
    is_corrupt, corrupt_reason = detect_numeric_corruption(text)
    operator, claims_unconditional = extract_numeric_operator(text)
    basis = extract_basis_from_text(text)
    qualifier = extract_qualifier_from_text(text)

    mentions = extract_all_numeric_mentions(text)
    if not mentions:
        return NormalizedNumericExpression(
            primary_value=None,
            primary_unit=None,
            canonical_value=None,
            canonical_unit=None,
            basis=basis,
            numeric_operator=operator,
            qualifier=qualifier,
            claims_unconditional_flat_rate=claims_unconditional,
            secondary_mentions=[],
            is_corrupted=is_corrupt,
            corruption_reason=corrupt_reason,
        )

    # Disambiguate primary claimed value when multiple mentions appear (e.g. condition trigger vs payout/rate)
    primary = mentions[0]
    secondary: list[NormalizedNumericMention] = []

    if len(mentions) > 1:
        candidates: list[NormalizedNumericMention] = []
        t_low = text.lower()
        for m in mentions:
            if (
                abs(m.value - 75.0) < 1e-6
                and "prevented" in t_low
                and any(abs(o.value - 75.0) > 1e-6 for o in mentions)
            ):
                secondary.append(m)
            elif (
                abs(m.value - 50.0) < 1e-6
                and ("expected yield" in t_low or "irrigated area" in t_low)
                and any(abs(o.value - 50.0) > 1e-6 for o in mentions)
            ):
                secondary.append(m)
            elif (
                abs(m.value - 7.0) < 1e-6
                and m.unit == "years"
                and ("out of" in t_low or "preceding 7" in t_low or "last 7" in t_low)
                and any(abs(o.value - 7.0) > 1e-6 for o in mentions)
            ):
                secondary.append(m)
            elif (
                m.value in (1.0, 1.2)
                and ("even if" in t_low or "even when" in t_low)
                and any(o.value not in (1.0, 1.2) for o in mentions)
            ):
                secondary.append(m)
            elif (
                m.canonical_unit == "kilometres"
                and ("beyond" in t_low or "outside" in t_low)
                and any(o.canonical_unit == "percent" for o in mentions)
            ):
                # e.g., "beyond 5 km radius, workers are paid 10% extra wages"
                secondary.append(m)
            elif (
                m.canonical_unit == "days"
                and abs(m.canonical_value - 30.0) < 1e-6
                and ("first 30 days" in t_low or "after 30 days" in t_low or "beyond 30 days" in t_low or "after the first 30 days" in t_low)
                and any(o.canonical_unit == "percent" for o in mentions)
            ):
                # e.g., "for the first 30 days, unemployment allowance is 25% of wage rate"
                secondary.append(m)
            elif (
                m.canonical_unit == "days"
                and m.canonical_value in (15.0, 16.0, 30.0)
                and ("delayed beyond" in t_low or "not made within" in t_low or "beyond 15 days" in t_low or "beyond 16 days" in t_low)
                and any(o.canonical_unit == "percent" for o in mentions)
            ):
                # e.g., "if wage payment is delayed beyond 15 days, compensation is 0.05% per day"
                secondary.append(m)
            elif (
                m.canonical_unit == "years"
                and abs(m.canonical_value - 70.0) < 1e-6
                and ("aged 70" in t_low or "above 70" in t_low or "70 years and above" in t_low or "70+" in t_low)
                and any(o.canonical_unit == "rupees" for o in mentions)
            ):
                # e.g., "senior citizens aged 70 years and above receive Rs 5,00,000 cover"
                secondary.append(m)
            elif (
                m.canonical_unit == "years"
                and abs(m.canonical_value - 6.0) < 1e-6
                and ("below 6 years" in t_low or "below the age of 6" in t_low or "under 6 years" in t_low)
                and any(o.canonical_unit == "children" for o in mentions)
            ):
                # e.g., "5 or more children below 6 years of age"
                secondary.append(m)
            elif (
                m.canonical_unit == "horsepower"
                and any(o.canonical_unit == "percent" for o in mentions)
                and ("subsidy" in t_low or "cfa" in t_low or "financial assistance" in t_low or "contribution" in t_low or "share" in t_low)
            ):
                # e.g., "for standalone solar pumps up to 7.5 HP, Central Government provides 30% CFA"
                secondary.append(m)
            elif (
                m.canonical_unit == "rupees"
                and re.search(rf"(?:above|more\s+than|exceeding)\s+{re.escape(m.raw_text)}", text, flags=re.IGNORECASE)
                and any(
                    o.canonical_unit == "rupees"
                    and o.canonical_value > m.canonical_value
                    and re.search(rf"(?:up\s+to|maximum|at\s+most|capped\s+at)\s+{re.escape(o.raw_text)}", text, flags=re.IGNORECASE)
                    for o in mentions
                )
            ):
                # e.g., "Kishore loans cover amounts above Rs 50,000 and up to Rs 5,00,000" -> 500,000 is the upper cap
                secondary.append(m)
            else:
                candidates.append(m)

        if candidates:
            primary = candidates[0]
            secondary.extend(candidates[1:])
        else:
            primary = mentions[0]
            secondary = mentions[1:]

    return NormalizedNumericExpression(
        primary_value=primary.value,
        primary_unit=primary.unit,
        canonical_value=primary.canonical_value,
        canonical_unit=primary.canonical_unit,
        basis=basis,
        numeric_operator=operator,
        qualifier=qualifier,
        claims_unconditional_flat_rate=claims_unconditional,
        secondary_mentions=secondary,
        is_corrupted=is_corrupt,
        corruption_reason=corrupt_reason,
    )


def compare_numeric_values(
    claimed_value: float,
    claimed_unit: str,
    rule_value: float,
    rule_unit: str,
    allowed_values: list[float] | None = None,
    rel_tol: float = 1e-6,
    abs_tol: float = 1e-6,
) -> tuple[bool, str]:
    """
    Compare a claimed (value, unit) against a rule's (maximum_rate, unit, allowed_values).
    Handles canonical unit conversions (e.g. '2 weeks' == '14 days', '3 days' == '72 hours',
    '5 years' == '60 months', '500 kW' == '0.5 MW')
    while strictly rejecting unit mismatches ('2%' != '2 days') and scale errors ('2%' != '0.02%').
    """
    _, c_norm_u, c_can_val, c_can_u = normalize_unit_and_value(claimed_value, claimed_unit)
    _, r_norm_u, r_can_val, r_can_u = normalize_unit_and_value(rule_value, rule_unit)

    # Support hours <-> days conversion when one is days and the other is hours
    if c_can_u == "days" and r_can_u == "hours":
        c_can_val = c_can_val * 24.0
        c_can_u = "hours"
    elif c_can_u == "hours" and r_can_u == "days":
        c_can_val = c_can_val / 24.0
        c_can_u = "days"
    # Support months <-> years conversion when one is years and the other is months
    elif c_can_u == "years" and r_can_u == "months":
        c_can_val = c_can_val * 12.0
        c_can_u = "months"
    elif c_can_u == "months" and r_can_u == "years":
        c_can_val = c_can_val / 12.0
        c_can_u = "years"
    # Support kilowatts <-> megawatts conversion
    elif c_can_u == "megawatts" and r_can_u == "kilowatts":
        c_can_val = c_can_val * 1000.0
        c_can_u = "kilowatts"
    elif c_can_u == "kilowatts" and r_can_u == "megawatts":
        c_can_val = c_can_val / 1000.0
        c_can_u = "megawatts"

    if c_can_u != r_can_u:
        return False, f"Unit mismatch: claimed '{claimed_unit}' ({c_can_u}) vs rule '{rule_unit}' ({r_can_u})"

    if allowed_values:
        for av in allowed_values:
            if math.isclose(c_can_val, float(av), rel_tol=rel_tol, abs_tol=abs_tol):
                return True, f"Matches allowed value {av} {r_can_u}"
        return False, f"Value {c_can_val} {c_can_u} not in allowed set {allowed_values}"

    if math.isclose(c_can_val, r_can_val, rel_tol=rel_tol, abs_tol=abs_tol):
        return True, f"Exact numerical match ({c_can_val} {c_can_u})"

    return False, f"Numerical value mismatch: claimed {c_can_val} {c_can_u} vs rule {r_can_val} {r_can_u}"
