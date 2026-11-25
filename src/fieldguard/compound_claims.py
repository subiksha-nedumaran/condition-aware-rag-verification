"""Separate explicitly linked PM-KISAN benefit figures for independent checks."""

from dataclasses import replace
import re

from fieldguard.claim_parser import ParsedClaim
from fieldguard.numeric_normalizer import extract_all_numeric_mentions


def pm_kisan_components(parsed: ParsedClaim) -> list[ParsedClaim]:
    if parsed.scheme != "PM_KISAN":
        return []
    text = re.sub(r"\s+", " ", parsed.raw_claim).lower()
    mentions = [m for m in extract_all_numeric_mentions(text) if m.unit != "hectares"]
    if len(mentions) < 2:
        return []
    components = []
    unsupported_qualification = bool(re.search(r"\b(?:not|never|at least|at most|more than|less than|maximum|minimum)\b", text))
    for mention in mentions:
        start = text.find(mention.raw_text.lower())
        before = text[:start]
        after = text[start + len(mention.raw_text):]
        parameter = basis = frequency = None
        if mention.unit == "instalments":
            parameter, basis, frequency = "instalments_per_year", "per_financial_year", "annual"
        elif mention.unit == "months":
            parameter, basis, frequency = "instalment_period_months", "per_instalment_window", "per_instalment"
        elif mention.unit == "rupees":
            if re.match(r"\s*(?:annually|per\s+(?:year|annum)|a\s+year|yearly)", after) or re.search(
                r"\b(?:annual|yearly|per\s+year|per\s+annum)\s+(?:income\s+|financial\s+)?(?:support|benefit|assistance)\s+of\s*$",
                before,
            ):
                parameter, basis, frequency = "annual_income_support", "per_eligible_farmer_family", "annual"
            elif re.match(r"\s*(?:each|per\s+instalment)", after) or re.search(
                r"\b(?:instalment|installment)\s+(?:amount\s+)?of\s*$",
                before,
            ):
                parameter, basis, frequency = "instalment_amount", "per_instalment", "per_instalment"
        component = replace(parsed, claimed_value=mention.value, claimed_unit=mention.unit,
            canonical_value=mention.canonical_value, canonical_unit=mention.canonical_unit,
            rule_parameter=parameter, basis=basis, frequency=frequency, season=frequency,
            parse_status="success" if parameter and not unsupported_qualification else "failed_malformed",
            uncertain_fields=[] if parameter and not unsupported_qualification else ["compound_numeric_role_or_qualification"],
            qualification=None, numeric_operator="eq")
        components.append(component)
    return components
