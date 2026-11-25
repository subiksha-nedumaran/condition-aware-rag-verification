"""Systematic rule-extraction engine for structured numerical facts in scheme evidence units.

Generates source-grounded StructuredRuleRecord objects for every numeric fact (amount,
percentage, duration, count, area, capacity) across paragraphs and table rows, including
scope conditions (beneficiary, geography, category, frequency, period) and qualifiers
("up to", "minimum", "whichever is less", etc.).

Reuses numeric_normalizer and uploaded_rules operator logic. Hand-curated rules always
take priority over auto-extracted ones.
"""

from __future__ import annotations

import re
from typing import Iterable

from fieldguard.evidence_schema import StructuredRuleRecord, validate_structured_rule_record
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import (
    NormalizedNumericMention,
    compare_numeric_values,
    extract_all_numeric_mentions,
    extract_basis_from_text,
    extract_numeric_operator,
    extract_qualifier_from_text,
    normalize_unit_and_value,
)
from fieldguard.uploaded_rules import _OPERATORS, extract_uploaded_candidates


def extract_table_cell_mentions_with_context(
    unit: ExtractedEvidenceUnit,
) -> list[tuple[NormalizedNumericMention, str]]:
    """Extract numeric mentions from table cells where units are encoded in column headers or Unit column."""
    if unit.evidence_type != "table_row" or not unit.headers or not unit.cells:
        return []

    results: list[tuple[NormalizedNumericMention, str]] = []
    header_map: dict[str, str] = {}
    for h, c in zip(unit.headers, unit.cells):
        header_map[h.strip()] = c.strip()

    explicit_unit_col = header_map.get("Unit") or header_map.get("Unit / Basis") or ""
    row_context = unit.text

    for h, c in zip(unit.headers, unit.cells):
        h_low = h.strip().lower()
        c_str = c.strip()
        if h_low in ("s.no.", "s.no", "sno", "sl.no", "row_id", "instalment_number"):
            continue

        m_num = re.fullmatch(r"(\d(?:[\d,]*\d)?(?:\.\d+)?)", c_str)
        if not m_num:
            continue
        val = float(m_num.group(1).replace(",", ""))

        inferred_unit: str | None = None
        if any(
            k in h_low
            for k in (
                "_inr",
                "rupee",
                "amount",
                "benefit",
                "grant",
                "loan",
                "assistance",
                "cost",
                "salary",
                "wage",
                "pension",
                "cap_inr",
                "min_inr",
                "max_inr",
            )
        ):
            inferred_unit = "rupees"
        elif any(k in h_low for k in ("_sqm", "sq_m", "area_sqm", "square_metre")):
            inferred_unit = "square_metres"
        elif any(k in h_low for k in ("_ha", "hectare")):
            inferred_unit = "hectares"
        elif any(k in h_low for k in ("_pct", "percent", "share", "rate", "ratio")):
            inferred_unit = "percent"
        elif any(k in h_low for k in ("_days", "days", "person_days")):
            inferred_unit = "days"
        elif any(k in h_low for k in ("_hp", "horsepower")):
            inferred_unit = "horsepower"
        elif any(k in h_low for k in ("_mw", "megawatt")):
            inferred_unit = "megawatts"
        elif any(k in h_low for k in ("_kw", "kilowatt")):
            inferred_unit = "kilowatts"
        elif any(k in h_low for k in ("_km", "kilometre", "distance")):
            inferred_unit = "kilometres"
        elif any(k in h_low for k in ("_months", "months", "tenure")):
            inferred_unit = "months"
        elif any(k in h_low for k in ("_years", "years", "age")):
            inferred_unit = "years"
        elif explicit_unit_col:
            inferred_unit = explicit_unit_col.split()[0].strip()

        if inferred_unit:
            norm_v, norm_u, can_v, can_u = normalize_unit_and_value(val, inferred_unit)
            mention = NormalizedNumericMention(
                raw_text=f"{h}: {c_str}" + (f" ({explicit_unit_col})" if explicit_unit_col else ""),
                value=norm_v,
                unit=norm_u,
                canonical_value=can_v,
                canonical_unit=can_u,
            )
            results.append((mention, f"{h}: {c_str} | {row_context}"))

    return results


def extract_unit_mentions_with_context(
    unit: ExtractedEvidenceUnit,
) -> list[tuple[NormalizedNumericMention, str]]:
    """Extract deduplicated numeric mentions and their local sentence/clause context from an evidence unit."""
    if unit.verification_status != "trusted_official":
        return []
    sec = (unit.section or "").upper()
    if sec in ("COVER", "TOC") or "METADATA NOTE" in sec:
        return []

    text = unit.text
    raw_inline = extract_all_numeric_mentions(text)
    items: list[tuple[NormalizedNumericMention, str]] = []

    for m in raw_inline:
        idx = text.find(m.raw_text)
        if idx >= 0:
            start = max(0, idx - 140)
            end = min(len(text), idx + len(m.raw_text) + 140)
            local_ctx = text[start:end]
        else:
            local_ctx = text
        items.append((m, local_ctx))

    items.extend(extract_table_cell_mentions_with_context(unit))

    deduped: list[tuple[NormalizedNumericMention, str]] = []
    for m, ctx in items:
        already = False
        for existing_m, _ in deduped:
            ok, _ = compare_numeric_values(
                m.canonical_value,
                m.canonical_unit,
                existing_m.canonical_value,
                existing_m.canonical_unit,
            )
            if ok:
                already = True
                break
        if not already:
            deduped.append((m, ctx))
    return deduped


def _is_mention_covered_by_rules(
    mention: NormalizedNumericMention,
    rules: Iterable[StructuredRuleRecord],
) -> bool:
    for r in rules:
        ok, _ = compare_numeric_values(
            claimed_value=mention.canonical_value,
            claimed_unit=mention.canonical_unit,
            rule_value=r.maximum_rate,
            rule_unit=r.unit,
            allowed_values=r.allowed_values,
        )
        if ok:
            return True
        if r.minimum_value is not None:
            ok_min, _ = compare_numeric_values(
                claimed_value=mention.canonical_value,
                claimed_unit=mention.canonical_unit,
                rule_value=r.minimum_value,
                rule_unit=r.unit,
            )
            if ok_min:
                return True
    return False


def _infer_geography(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("north eastern", "north-eastern", "ner ", "himalayan", "sikkim", "assam")):
        if "hilly" in t or "difficult" in t or "iap" in t:
            return "hilly_and_difficult_areas"
        return "north_eastern_states"
    if any(k in t for k in ("hilly", "difficult area", "iap", "integrated action plan")):
        return "hilly_and_difficult_areas"
    if any(k in t for k in ("plain area", "plains")):
        return "plains_areas"
    if any(k in t for k in ("union territor", "without legislature", "ladakh", "lakshadweep", "andaman")):
        return "union_territories"
    if any(k in t for k in ("drought", "natural calamity", "forest rights act", "fra ")):
        return "drought_or_calamity_notified_areas"
    if "general state" in t:
        return "general_states"
    return "all_india"


def _infer_frequency_and_season(text: str, scheme: str) -> tuple[str, str]:
    t = text.lower()
    if scheme == "PMFBY":
        if "kharif" in t and "rabi" not in t:
            return "kharif", "kharif"
        if "rabi" in t and "kharif" not in t:
            return "rabi", "rabi"
    if any(
        k in t
        for k in (
            "four-monthly",
            "four monthly",
            "per instalment",
            "each instalment",
            "first instalment",
            "second instalment",
            "third instalment",
        )
    ):
        return "per_instalment", "four_monthly"
    if any(k in t for k in ("monthly", "per month")):
        return "monthly", "monthly"
    if any(k in t for k in ("per day", "daily", "each day")):
        return "per_day", "annual"
    if any(k in t for k in ("weekly", "each week", "per week")):
        return "weekly", "annual"
    if any(k in t for k in ("every 6 months", "six months", "semi-annual", "half-yearly")):
        return "semi_annual", "annual"
    if any(k in t for k in ("one-time", "one time", "unit assistance", "capital subsidy")):
        return "one_time", "annual"
    return "annual", "annual"


def _infer_operator_and_qualifier(local_ctx: str, unit_text: str) -> tuple[str, str | None, bool]:
    op_norm, _ = extract_numeric_operator(local_ctx)
    op_up = "eq"
    for pattern, val in _OPERATORS:
        if re.search(pattern, local_ctx, flags=re.IGNORECASE):
            op_up = val
            break
    op = op_norm if op_norm != "eq" else op_up

    qual = extract_qualifier_from_text(local_ctx) or extract_qualifier_from_text(unit_text)
    requires_qual = bool(qual == "or_actuarial_rate_whichever_is_less")

    t_low = local_ctx.lower()
    if qual is None:
        if "whichever is lower" in t_low or "whichever is less" in t_low:
            qual = "whichever_is_lower"
        elif "up to" in t_low or "maximum" in t_low or "capped at" in t_low or "not exceeding" in t_low:
            qual = "maximum_ceiling"
        elif "at least" in t_low or "not less than" in t_low or "minimum" in t_low:
            qual = "minimum_entitlement"
        elif "only" in t_low or "exclusively" in t_low:
            qual = "restricted_condition"
        elif "excluding" in t_low or "except" in t_low:
            qual = "subject_to_statutory_exemption"

    return op, qual, requires_qual


def _infer_parameter_and_scope(
    scheme: str,
    mention: NormalizedNumericMention,
    local_ctx: str,
    unit: ExtractedEvidenceUnit,
) -> tuple[str, str, str | None]:
    """Infer (rule_parameter, entity_scope, basis) from scheme, mention, and context."""
    t = f"{local_ctx} {unit.section or ''} {unit.text}".lower()
    local_low = local_ctx.lower()
    val = mention.canonical_value
    u = mention.canonical_unit
    basis = extract_basis_from_text(local_ctx) or extract_basis_from_text(unit.text)

    if scheme == "PMFBY":
        if "betelvine" in t:
            return "farmer_premium_rate_betelvine_conflict_notice", "perennial_betelvine_pilot", "sum_insured"
        if "cce" in local_low or "crop cutting" in local_low or u == "cces":
            if val == 4.0 or "gram panchayat" in local_low:
                return "gp_cce_minimum_count", "gram_panchayat_major_crops", "crop_cutting_experiments"
            return "mandal_cce_minimum_count", "mandal_taluka_level", "crop_cutting_experiments"
        if "women" in local_low and "outreach" in t:
            return "women_outreach_participation_target", "women_and_small_farmers_outreach", "outreach_participation"
        if u == "hectares" and ("outreach" in t or "small/marginal" in local_low):
            return "small_farmer_landholding_threshold_ha", "small_and_marginal_farmers_outreach", "operational_landholding"
        if "camp" in local_low or "blocks each week" in local_low:
            return "weekly_block_camp_coverage_target", "digital_village_camps", "high_priority_blocks_per_week"
        if "wild animal" in t and val == 0.0:
            return "wild_animal_addon_central_subsidy_share", "wild_animal_attack_addon", "wild_animal_addon_cost"
        if "1.2%" in local_low and ("example" in local_low or "bidding actuarial" in local_low):
            return "illustrative_lower_actuarial_rate_example", "food_grain_and_oilseed", "sum_insured"
        if val == 10.0 and u == "percent" and ("north eastern" in t or "90:10" in t):
            return "state_subsidy_share_ner", "all_notified_crops", "normal_premium_subsidy"
        if val == 75.0 and u == "percent" and "prevented" in t:
            return "prevented_sowing_area_trigger_pct", "all_notified_crops", "notified_sown_area"
        if val == 50.0 and u == "percent" and "expected yield" in t:
            return "mid_season_adversity_yield_trigger_pct", "all_notified_crops", "threshold_yield"
        if val == 50.0 and u == "percent" and "irrigated area" in local_low:
            return "irrigated_district_classification_threshold_pct", "irrigated_crops", "district_irrigated_area"
        if val == 7.0 and u == "years" and ("preceding 7" in t or "last 7" in t):
            return "threshold_yield_lookback_window_years", "all_notified_crops", "preceding_7_years_yield_history"
        if "clause 3.1" in (unit.section or "").lower() and val == 100.0:
            return "voluntary_enrolment_share_pct", "all_farmers_2023", "all_loanee_and_non_loanee_farmers"
        if "clause 4.2" in (unit.section or "").lower() and val == 100.0:
            return "sum_insured_scale_of_finance_share_pct", "all_notified_crops", "scale_of_finance"
        if unit.evidence_type == "table_row":
            # Secondary qualification cross-reference inside a table row that already has a primary rule
            return f"table_qualification_reference_{u}_{int(val)}", "table_qualification_scope", basis

    if scheme == "PM_KISAN":
        if val == 145000000.0 or (u == "farmers" and "14.5 crore" in local_low):
            return "estimated_national_beneficiary_coverage", "all_landholding_farmers", "national_farmer_families"
        if u == "acres" or (val == 5.0 and "acres" in local_low):
            return "landholding_eligibility_cap_acres_hist", "small_and_marginal_farmers", "combined_cultivable_landholding"
        if val == 2.0 and u == "hectares" and "removes the 2 hectare ceiling" in local_low:
            return "removed_landholding_ceiling_ha", "all_landholding_farmers", "combined_cultivable_landholding"

    # Generic fallback parameter naming
    clean_sec = re.sub(r"[^a-z0-9]+", "_", (unit.section or "clause").lower()).strip("_")
    param = f"rule_{u}_{int(val) if val.is_integer() else str(val).replace('.', 'p')}_{clean_sec[:20]}"
    scope = "general_beneficiaries"
    return param, scope, basis


def extract_structured_rules_from_units(
    scheme: str,
    units: Iterable[ExtractedEvidenceUnit],
    curated_rules: Iterable[StructuredRuleRecord],
) -> list[StructuredRuleRecord]:
    """
    Combine hand-curated rules (which take priority) with systematically auto-extracted
    StructuredRuleRecord objects for any numeric facts in trusted evidence units not yet
    covered on their respective evidence_id.
    """
    scheme_upper = scheme.upper()
    curated_list = list(curated_rules)
    unit_list = list(units)

    # Index curated rules by evidence_id
    by_ev_id: dict[str, list[StructuredRuleRecord]] = {}
    for r in curated_list:
        by_ev_id.setdefault(r.evidence_id, []).append(r)

    # Track conflict keys of curated rules so auto-extracted rules never collide with a different rate
    existing_conflict_keys: dict[tuple[object, ...], float] = {}
    existing_rule_ids: set[str] = {r.rule_id for r in curated_list}
    for r in curated_list:
        ckey = (
            r.scheme,
            r.rule_parameter,
            r.entity_scope or r.crop_category,
            r.frequency or r.season,
            r.geography,
            r.policy_era,
        )
        existing_conflict_keys[ckey] = round(r.maximum_rate, 6)

    auto_rules: list[StructuredRuleRecord] = []

    for unit in unit_list:
        if unit.verification_status != "trusted_official":
            continue
        unit_rules = list(by_ev_id.get(unit.evidence_id, []))
        mentions_with_ctx = extract_unit_mentions_with_context(unit)

        for idx, (mention, local_ctx) in enumerate(mentions_with_ctx, start=1):
            if _is_mention_covered_by_rules(mention, unit_rules):
                continue

            explicit_param, explicit_scope, explicit_basis = _infer_parameter_and_scope(
                scheme_upper, mention, local_ctx, unit
            )

            matched_curated: StructuredRuleRecord | None = None
            if explicit_param.startswith("rule_"):
                # Try matching against existing curated rules in the scheme
                candidates: list[StructuredRuleRecord] = []
                for cr in curated_list:
                    if cr.conflict_flag or "ADDENDUM_BETELVINE" in cr.rule_id:
                        continue
                    ok, _ = compare_numeric_values(
                        mention.canonical_value,
                        mention.canonical_unit,
                        cr.maximum_rate,
                        cr.unit,
                        allowed_values=cr.allowed_values,
                    )
                    if ok:
                        candidates.append(cr)

                if candidates:
                    t_low = f"{local_ctx} {unit.text}".lower()
                    best_cr = candidates[0]
                    best_score = -1
                    for cr in candidates:
                        sc = 0
                        if cr.policy_era == unit.policy_era:
                            sc += 3
                        if cr.season and cr.season.lower() in t_low:
                            sc += 2
                        if cr.crop_category and any(
                            w in t_low for w in cr.crop_category.lower().split("_") if len(w) > 3
                        ):
                            sc += 2
                        if cr.geography and any(
                            w in t_low for w in cr.geography.lower().split("_") if len(w) > 3
                        ):
                            sc += 2
                        if sc > best_score:
                            best_score = sc
                            best_cr = cr
                    matched_curated = best_cr

            if matched_curated is not None:
                rule_param = matched_curated.rule_parameter
                season = matched_curated.season
                crop_cat = matched_curated.crop_category
                geog = matched_curated.geography
                min_val = matched_curated.minimum_value
                max_val = matched_curated.maximum_rate
                allowed_vals = (
                    list(matched_curated.allowed_values) if matched_curated.allowed_values else None
                )
                num_op = matched_curated.numeric_operator
                r_unit = matched_curated.unit
                r_basis = matched_curated.basis
                r_qual = matched_curated.qualifier
                req_qual = matched_curated.requires_qualifier_for_unconditional_claim
                ent_scope = matched_curated.entity_scope
                conds = dict(matched_curated.conditions) if matched_curated.conditions else {}
                excls = list(matched_curated.exclusions) if matched_curated.exclusions else []
                freq = matched_curated.frequency
            else:
                rule_param = explicit_param
                freq, season = _infer_frequency_and_season(local_ctx, scheme_upper)
                geog = _infer_geography(local_ctx)
                num_op, r_qual, req_qual = _infer_operator_and_qualifier(local_ctx, unit.text)
                crop_cat = explicit_scope
                ent_scope = explicit_scope
                min_val = mention.canonical_value if num_op in ("ge", "eq") else None
                max_val = mention.canonical_value
                allowed_vals = [mention.canonical_value] if num_op == "eq" else None
                r_unit = mention.canonical_unit
                r_basis = explicit_basis or f"per_{r_unit}_statutory_norm"
                r_qual = r_qual or "official_guideline_provision"
                conds = {"beneficiary_type": explicit_scope, "geography": geog}
                excls = []

            r_basis = r_basis or f"per_{r_unit}_statutory_norm"
            r_qual = r_qual or "official_guideline_provision"

            ckey = (
                scheme_upper,
                rule_param,
                ent_scope or crop_cat,
                freq or season,
                geog,
                unit.policy_era,
            )
            if (
                ckey in existing_conflict_keys
                and abs(existing_conflict_keys[ckey] - round(max_val, 6)) > 1e-6
            ):
                ent_scope = f"{ent_scope}_{unit.evidence_id.lower()}"
                crop_cat = ent_scope
                ckey = (
                    scheme_upper,
                    rule_param,
                    ent_scope,
                    freq or season,
                    geog,
                    unit.policy_era,
                )

            base_id = f"RULE_AUTO_{scheme_upper}_{unit.evidence_id}_{idx}"
            rule_id = base_id
            suffix = 1
            while rule_id in existing_rule_ids:
                suffix += 1
                rule_id = f"{base_id}_{suffix}"
            existing_rule_ids.add(rule_id)

            new_rule = StructuredRuleRecord(
                rule_id=rule_id,
                evidence_id=unit.evidence_id,
                scheme=scheme_upper,
                rule_parameter=rule_param,
                season=season,
                crop_category=crop_cat,
                geography=geog,
                minimum_value=min_val,
                maximum_rate=max_val,
                allowed_values=allowed_vals,
                numeric_operator=num_op,
                unit=r_unit,
                basis=r_basis,
                qualifier=r_qual,
                requires_qualifier_for_unconditional_claim=req_qual,
                source_document_id=unit.document_id,
                document_version=unit.document_version or "official",
                policy_era=unit.policy_era or "current",
                publication_date=unit.publication_date,
                section=unit.section or "Section 1",
                physical_pdf_page=unit.physical_pdf_page if unit.physical_pdf_page is not None else 1,
                printed_page=unit.printed_page,
                table_id=unit.table_id,
                row_id=unit.row_id,
                effective_from=unit.effective_from,
                effective_to=unit.effective_to,
                verification_status=unit.verification_status,
                entity_scope=ent_scope,
                conditions=conds,
                exclusions=excls,
                frequency=freq,
            )
            valid, _ = validate_structured_rule_record(new_rule)
            if valid:
                auto_rules.append(new_rule)
                unit_rules.append(new_rule)
                existing_conflict_keys[ckey] = round(max_val, 6)

    return curated_list + auto_rules
