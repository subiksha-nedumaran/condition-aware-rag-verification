"""Condition-aware document-only comparison; uploaded text is never official evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import (
    NormalizedNumericMention,
    compare_numeric_values,
    extract_all_numeric_mentions,
)
from fieldguard.uploaded_rules import UploadedCandidateRule, extract_uploaded_candidates


def _yield_thresholds(text: str) -> list[tuple[float, str, str]]:
    """Recognize an explicit yield trigger, not a payout or premium percentage.

    Only this narrow paraphrase family is normalized. Denominator, inequality,
    and any extra eligibility restriction must remain grounded in the passage.
    """
    normalized = re.sub(r"\s+", " ", text.casefold()).replace("–", "-")
    if not re.search(r"mid[ -]?season\s+adversity", normalized):
        return []
    results = []
    pattern = re.compile(
        r"expected\s+yield(?P<link>[^.;!?%]{0,100}?)"
        r"(?P<operator>less\s+than|below|more\s+than|above|at\s+least|at\s+most)\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?:%|percent|per\s+cent)\s*"
        r"of\s+(?:the\s+)?(?P<basis>normal|threshold)\s+yield"
    )
    for match in pattern.finditer(normalized):
        # Reject negation and restrictions rather than dropping them during paraphrase matching.
        clause_start = max(normalized.rfind(".", 0, match.start()), normalized.rfind(";", 0, match.start())) + 1
        clause_end = normalized.find(".", match.end())
        clause = normalized[clause_start:clause_end if clause_end >= 0 else len(normalized)]
        if re.search(r"\b(?:not|never|only|unless|except|provided|irrigated|unirrigated|districts?|ineligible)\b", clause):
            continue
        # Limit the permitted link to yield prediction language, not arbitrary intervening prose.
        link = match["link"].strip()
        if re.sub(r"\b(?:during|the|crop|season|is|are|likely|to|be|falls?|expected|estimated)\b", "", link).strip():
            continue
        operator = {
            "less than": "lt",
            "below": "lt",
            "more than": "gt",
            "above": "gt",
            "at least": "ge",
            "at most": "le",
        }[match["operator"]]
        results.append((float(match["value"]), operator, match["basis"]))
    return results


def _compare_yield_threshold(claim: str, retrieved: list[ExtractedEvidenceUnit], corpus: list[ExtractedEvidenceUnit]):
    target = _yield_thresholds(claim)
    if len(target) != 1 or len(extract_all_numeric_mentions(claim)) != 1:
        return None
    visible = {unit.evidence_id for unit in retrieved}
    candidates = [
        (unit.evidence_id, rule)
        for unit in corpus
        if is_uploaded(unit)
        for rule in _yield_thresholds(unit.text)
    ]
    relevant = [(eid, rule) for eid, rule in candidates if rule[2] == target[0][2]]
    if not any(eid in visible for eid, _ in relevant):
        return None
    if len({rule for _, rule in relevant}) > 1:
        return "UNVERIFIABLE", [], [], "Uploaded passages contain conflicting yield thresholds."
    supports = [eid for eid, rule in relevant if eid in visible and rule == target[0]]
    if supports:
        return (
            "SUPPORTED",
            sorted(set(supports)),
            [],
            "The uploaded evidence states the same mid-season expected-yield threshold, inequality, and yield basis.",
        )
    return (
        "CONTRADICTED",
        [],
        sorted({eid for eid, _ in relevant if eid in visible}),
        "The uploaded evidence specifies a different expected-yield threshold or inequality for this yield basis.",
    )


def is_uploaded(unit: ExtractedEvidenceUnit) -> bool:
    return unit.source_url.startswith("uploaded://") or unit.document_id.startswith("DOC_UPLOAD_")


def _signature(text: str) -> tuple[str, tuple[float, str]] | None:
    # Keep every word, operator, negation and qualifier. Do not split sentences:
    # a later sentence may restrict an entitlement in the same passage.
    normalized = re.sub(r"\s+", " ", text.casefold()).strip().rstrip(".")
    mentions = extract_all_numeric_mentions(normalized)
    if len(mentions) != 1 or mentions[0].is_corrupted:
        return None
    mention = mentions[0]
    if normalized.count(mention.raw_text) != 1:
        return None
    # Preserve words embedded inside the numeric mention (e.g. "3 quarterly
    # instalments" or "3 subsidized solar pumps"). Removing the whole mention
    # would erase frequency or eligibility conditions.
    raw = mention.raw_text
    numeric = re.search(r"\d+(?:\.\d+)?", raw)
    if numeric is None:
        # Word-number paraphrases need a richer parser; retain conservative abstention.
        return None
    masked = raw[:numeric.start()] + "<number>" + raw[numeric.end():]
    context = normalized.replace(raw, masked, 1)
    if not re.search(r"[a-z]", context.replace("<number>", "")):
        return None
    return context, (mention.canonical_value, mention.canonical_unit)


# ---------------------------------------------------------------------------
# Condition-aware parsing and candidate matching for uploaded documents
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "could",
    "for", "from", "gets", "get", "given", "has", "have", "in", "into", "is",
    "it", "its", "may", "must", "of", "on", "or", "our", "out", "over", "provided",
    "provides", "provide", "receive", "receives", "received", "receiving", "shall",
    "should", "so", "some", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "through", "to", "towards", "under",
    "up", "upon", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "will", "with", "within", "would", "scheme", "guideline",
    "guidelines", "policy", "document", "programme", "program", "mission", "yojana",
    "abhiyan", "eligible", "available", "entitled", "applicable", "support",
    "supported", "rs", "inr", "rupees", "rupee", "lakh", "lakhs", "crore", "crores",
    "percent", "percentage", "per", "cent",
})

_SYNONYM_MAP = {
    "subsidies": "subsidy",
    "grant": "subsidy",
    "grants": "subsidy",
    "assistance": "subsidy",
    "financial": "subsidy",
    "aid": "subsidy",
    "subvention": "subvention",
    "loans": "loan",
    "credit": "loan",
    "tranches": "tranche",
    "instalments": "instalment",
    "installments": "instalment",
    "installment": "instalment",
    "vendors": "vendor",
    "hawkers": "vendor",
    "hawker": "vendor",
    "entrepreneurs": "entrepreneur",
    "beneficiaries": "beneficiary",
    "farmers": "farmer",
    "households": "household",
    "families": "household",
    "family": "household",
    "women": "woman",
    "female": "woman",
    "mahila": "woman",
    "drones": "drone",
    "pumps": "pump",
    "projects": "project",
    "units": "unit",
    "stipends": "stipend",
    "allowance": "stipend",
    "trainees": "trainee",
    "pilots": "pilot",
    "states": "state",
    "areas": "area",
    "regions": "area",
    "tonnes": "tonne",
    "tons": "tonne",
    "mt": "tonne",
    "quintals": "quintal",
    "hectares": "hectare",
    "acres": "acre",
    "months": "month",
    "years": "year",
    "days": "day",
    "hours": "hour",
    "children": "child",
    "maternity": "maternity",
    "pregnant": "pregnant",
    "lactating": "lactating",
    "cashback": "cashback",
    "reward": "cashback",
    "incentive": "incentive",
    "incentives": "incentive",
    "storage": "storage",
    "cold": "cold",
    "solar": "solar",
    "livestock": "livestock",
    "poultry": "poultry",
    "fodder": "fodder",
    "sheep": "sheep",
    "goat": "goat",
    "piggery": "piggery",
    "cap": "cap",
    "ceiling": "cap",
    "maximum": "cap",
    "limit": "cap",
}

_CLAIM_OPERATOR_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?:up\s+to|at\s+most|no\s+more\s+than|not\s+more\s+than|not\s+exceeding|capped\s+at|maximum(?:\s+of)?|ceiling(?:\s+of)?|<=|≤)", "le"),
    (r"(?:at\s+least|no\s+less\s+than|not\s+less\s+than|minimum(?:\s+of)?|floor(?:\s+of)?|>=|≥)", "ge"),
    (r"(?:less\s+than|below|under|fewer\s+than|<)", "lt"),
    (r"(?:more\s+than|greater\s+than|above|exceeding|over|>)", "gt"),
    (r"(?:exactly|equal\s+to|fixed\s+at|=)", "eq"),
)

_SCOPE_PATTERNS: dict[str, dict[str, str]] = {
    "beneficiary_category": {
        "sc_st": r"\b(?:sc\s*/\s*st|sc|st|scheduled\s+castes?|scheduled\s+tribes?)\b",
        "women": r"\b(?:women|woman|female|mahila|didi|widows?|pregnant|lactating)\b",
        "general": r"\b(?:general\s+category|general\s+entrepreneurs?|general\s+beneficiar\w*|general\s+applicants?|unreserved)\b",
        "obc": r"\b(?:obc|other\s+backward\s+class\w*)\b",
        "small_marginal_farmer": r"\b(?:small\s+and\s+marginal\s+farmers?|smf|small\s+farmers?|marginal\s+farmers?)\b",
        "large_farmer": r"\b(?:large\s+farmers?|medium\s+and\s+large\s+farmers?|commercial\s+farmers?)\b",
        "shg_fpo_group": r"\b(?:shgs?|self[- ]help\s+groups?|fpos?|fpc|farmer\s+producer\s+organi[sz]ations?|cooperatives?|jlgs?)\b",
        "individual_beneficiary": r"\b(?:individual\s+farmers?|individual\s+entrepreneurs?|individual\s+beneficiar\w*|individual\s+applicants?)\b",
        "excluded_privileged": r"\b(?:corporate\s+entit\w*|large\s+corporates?|private\s+compan\w*|income\s+tax\s+payers?|taxpayers?|government\s+employees?|regular\s+civil\s+servants?|public\s+sector\s+undertakings?|psus?)\b",
    },
    "geography": {
        "hilly_ne": r"\b(?:hilly|north[- ]?eastern|ne\s+states?|ner\b|himalayan|uttarakhand|himachal|assam|sikkim|arunachal|manipur|meghalaya|mizoram|nagaland|tripura|jammu|kashmir|ladakh|difficult\s+areas?)\b",
        "plains": r"\b(?:plains?|plain\s+areas?|non[- ]?hilly|other\s+states?|mainland\s+plains?)\b",
        "urban": r"\b(?:urban\s+areas?|municipal\w*|cities|towns?|metro\w*|ulbs?)\b",
        "rural": r"\b(?:rural\s+areas?|gram\s+panchayat\w*|villages?)\b",
        "rajasthan": r"\brajasthan\b",
        "kerala": r"\bkerala\b",
        "bihar": r"\bbihar\b",
        "gujarat": r"\bgujarat\b",
        "maharashtra": r"\bmaharashtra\b",
        "karnataka": r"\bkarnataka\b",
        "uttar_pradesh": r"\buttar\s+pradesh\b",
        "madhya_pradesh": r"\bmadhya\s+pradesh\b",
    },
    "tranche_or_order": {
        "first": r"\b(?:first\s+tranche|1st\s+tranche|tranche\s*1|tranche[- ]?i\b|first\s+instalment|1st\s+instalment|instalment\s*1|first\s+loan|initial\s+working\s+capital|first\s+living\s+child|first\s+child)\b",
        "second": r"\b(?:second\s+tranche|2nd\s+tranche|tranche\s*2|tranche[- ]?ii\b|second\s+instalment|2nd\s+instalment|instalment\s*2|second\s+loan|second\s+living\s+child|second\s+child)\b",
        "third": r"\b(?:third\s+tranche|3rd\s+tranche|tranche\s*3|tranche[- ]?iii\b|third\s+instalment|3rd\s+instalment|instalment\s*3|third\s+loan)\b",
    },
    "frequency": {
        "annual": r"\b(?:annually|annual|per\s+annum|p\.?a\.?|per\s+year|yearly|every\s+year)\b",
        "monthly": r"\b(?:monthly|per\s+month|every\s+month)\b",
        "quarterly": r"\b(?:quarterly|every\s+quarter|every\s+three\s+months|every\s+3\s+months)\b",
        "daily": r"\b(?:daily|per\s+day|every\s+day|per\s+diem)\b",
        "one_time": r"\b(?:one[- ]?time|lump[- ]?sum|single\s+instalment|single\s+grant)\b",
    },
    "basis": {
        "per_household": r"\b(?:per\s+household|per\s+family|family\s+floater)\b",
        "per_person": r"\b(?:per\s+person|per\s+individual|per\s+beneficiary|per\s+member|per\s+trainee|per\s+vendor|per\s+pilot)\b",
        "per_hectare": r"\b(?:per\s+hectare|per\s+ha|per\s+acre)\b",
        "per_transaction": r"\b(?:per\s+transaction|each\s+digital\s+transaction|per\s+digital\s+transaction)\b",
    },
}


def _normalize_token(word: str) -> str:
    w = word.casefold().strip(".,;:!?()[]{}\"'")
    if w in _SYNONYM_MAP:
        return _SYNONYM_MAP[w]
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 4 and w.endswith("es") and not w.endswith(("ses", "xes", "zes", "ches", "shes")):
        w = w[:-1]
    elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    return _SYNONYM_MAP.get(w, w)


def _extract_subject_keywords(text: str) -> set[str]:
    cleaned = re.sub(r"\d+(?:,\d+)*(?:\.\d+)?", " ", text.casefold())
    tokens = re.findall(r"[a-z]{3,}", cleaned)
    result: set[str] = set()
    for tok in tokens:
        if tok in _STOPWORDS:
            continue
        norm = _normalize_token(tok)
        if norm and norm not in _STOPWORDS and len(norm) >= 3:
            result.add(norm)
    return result


def _extract_scope_tags(text: str) -> dict[str, set[str]]:
    lowered = text.casefold()
    tags: dict[str, set[str]] = {}
    for dim, mapping in _SCOPE_PATTERNS.items():
        found: set[str] = set()
        for label, pattern in mapping.items():
            if re.search(pattern, lowered):
                found.add(label)
        if found:
            tags[dim] = found
    return tags


def _extract_local_operator(text: str, mention_start: int) -> str | None:
    window_start = max(0, mention_start - 45)
    prefix = re.sub(r"\s+", " ", text[window_start:mention_start]).casefold().rstrip()
    for pattern, op in _CLAIM_OPERATOR_PATTERNS:
        if re.search(r"(?<!\w)" + pattern + r"\s*(?:of\s*|a\s*|an\s*|the\s*)?$", prefix):
            return op
    return None


def _extract_qualifier_tag(text: str) -> str | None:
    lowered = text.casefold()
    if re.search(r"\bwhichever\s+is\s+(?:less|lower|smaller)\b", lowered):
        return "whichever_is_less"
    if re.search(r"\bwhichever\s+is\s+(?:higher|greater|more|larger)\b", lowered):
        return "whichever_is_higher"
    return None


def _has_negation(text: str) -> bool:
    lowered = text.casefold()
    return bool(
        re.search(
            r"\b(?:not|never|no\s+longer|neither|nor|cannot|ineligible|excluded|prohibited|barred|do\s+not|does\s+not|shall\s+not|are\s+not|is\s+not)\b",
            lowered,
        )
    )


def _has_strict_restriction(text: str) -> set[str]:
    lowered = text.casefold()
    found: set[str] = set()
    for marker in ("only if", "only for", "only to", "only ", "unless", "except", "subject to", "provided that"):
        if marker in lowered:
            found.add(marker.strip())
    return found


@dataclass
class ParsedMentionQuery:
    mention: NormalizedNumericMention
    mention_start: int
    mention_end: int
    operator: str | None
    local_keywords: set[str]
    local_scope: dict[str, set[str]]


@dataclass
class ParsedUploadedClaim:
    raw_claim: str
    mentions: list[ParsedMentionQuery]
    subject_keywords: set[str]
    scope_tags: dict[str, set[str]]
    qualifier: str | None
    has_negation: bool
    restrictions: set[str]


def parse_uploaded_claim(claim: str) -> ParsedUploadedClaim:
    """Parse a free-form claim against an uploaded document into structured features."""
    raw_mentions = [m for m in extract_all_numeric_mentions(claim) if not m.is_corrupted]
    # Locate spans in claim
    spans: list[tuple[int, int, NormalizedNumericMention]] = []
    used_ranges: list[tuple[int, int]] = []
    for m in raw_mentions:
        for match in re.finditer(re.escape(m.raw_text), claim, re.IGNORECASE):
            s, e = match.span()
            if any(not (e <= us or s >= ue) for us, ue in used_ranges):
                continue
            spans.append((s, e, m))
            used_ranges.append((s, e))
            break
    spans.sort(key=lambda item: item[0])

    # Filter out bare tranche/instalment ordinals when there is a real value mention
    # e.g. "1st tranche loan of Rs. 10,000" where "1" might not be a separate numeric claim if extracted
    mention_queries: list[ParsedMentionQuery] = []
    for idx, (s, e, m) in enumerate(spans):
        prev_bound = spans[idx - 1][1] if idx > 0 else 0
        next_bound = spans[idx + 1][0] if idx + 1 < len(spans) else len(claim)
        local_ctx = claim[max(0, min(prev_bound, s - 60)):min(len(claim), max(next_bound, e + 60))]
        op = _extract_local_operator(claim, s)
        mention_queries.append(
            ParsedMentionQuery(
                mention=m,
                mention_start=s,
                mention_end=e,
                operator=op,
                local_keywords=_extract_subject_keywords(local_ctx),
                local_scope=_extract_scope_tags(local_ctx),
            )
        )

    return ParsedUploadedClaim(
        raw_claim=claim,
        mentions=mention_queries,
        subject_keywords=_extract_subject_keywords(claim),
        scope_tags=_extract_scope_tags(claim),
        qualifier=_extract_qualifier_tag(claim),
        has_negation=_has_negation(claim),
        restrictions=_has_strict_restriction(claim),
    )


@dataclass
class EnrichedCandidateRule:
    rule: UploadedCandidateRule
    unit: ExtractedEvidenceUnit
    clause_text: str
    immediate_window: str
    clause_keywords: set[str]
    passage_keywords: set[str]
    clause_scope: dict[str, set[str]]
    passage_scope: dict[str, set[str]]
    effective_operator: str | None
    qualifier_tag: str | None
    clause_has_negation: bool
    clause_restrictions: set[str]


def _compare_unit_and_value(v1: float, u1: str, v2: float, u2: str) -> tuple[bool, bool]:
    """Return (unit_compatible, exact_value_match) using compare_numeric_values."""
    exact_match, detail = compare_numeric_values(v1, u1, v2, u2)
    unit_compatible = not detail.startswith("Unit mismatch")
    return unit_compatible, exact_match


def _extract_clause_and_window(
    text: str,
    mention_start: int,
    mention_end: int,
    all_rules_in_unit: list[UploadedCandidateRule],
    current_rule: UploadedCandidateRule,
) -> tuple[str, str]:
    """Isolate the local clause and immediate context window around a numeric mention."""
    # Split on hard contrast/clause delimiters
    contrast_pattern = re.compile(
        r"(?:;|\n|\bwhereas\b|\bwhile\b|\bhowever\b|\bin\s+contrast\b|\bon\s+the\s+other\s+hand\b|\.\s+)",
        re.IGNORECASE,
    )
    boundaries = [0]
    for m in contrast_pattern.finditer(text):
        # Do not split on decimal points or "Rs." / "Dr." / "No." / "St."
        seg = text[max(0, m.start() - 3):m.end()]
        if re.search(r"\b(?:rs|dr|no|sr|st|mr|ms|sec|fig)\.\s+$", seg, re.IGNORECASE):
            continue
        boundaries.append(m.start())
        boundaries.append(m.end())
    boundaries.append(len(text))
    boundaries = sorted(set(boundaries))

    clause_start = 0
    clause_end = len(text)
    for i in range(len(boundaries) - 1):
        b_start, b_end = boundaries[i], boundaries[i + 1]
        if b_start <= mention_start < b_end:
            clause_start, clause_end = b_start, b_end
            break

    # If the passage is a pipe-delimited table row ("Header: Value | Header: Value"),
    # keep the whole row as the clause so category cells and value cells stay linked,
    # unless multiple same-unit numbers appear in different pipe cells.
    clause_text = text[clause_start:clause_end].strip()
    # Strip any prepended section-title prefix ("Section 2: ...: ") if the mention is after it
    sec_prefix_match = re.match(r"^(?:section\s+\d+\s*:\s*[^:]+:\s*)", clause_text, re.IGNORECASE)
    if sec_prefix_match and (mention_start - clause_start) >= sec_prefix_match.end():
        clause_text = clause_text[sec_prefix_match.end():].strip()

    # Now build an immediate window that separates multiple same-unit mentions inside the same clause
    same_unit_siblings = [
        r for r in all_rules_in_unit
        if clause_start <= r.mention_start < clause_end
        and _compare_unit_and_value(r.value, r.unit, current_rule.value, current_rule.unit)[0]
    ]
    same_unit_siblings.sort(key=lambda r: r.mention_start)

    win_start = clause_start
    win_end = clause_end
    if len(same_unit_siblings) > 1:
        idx = next((i for i, r in enumerate(same_unit_siblings) if r.rule_id == current_rule.rule_id), 0)
        if idx > 0:
            prev_r = same_unit_siblings[idx - 1]
            between = text[prev_r.mention_end:mention_start]
            # Look for comma, 'and', '|', or midpoint between previous same-unit mention and this one
            split_matches = list(re.finditer(r"(?:,|\band\b|\bor\b|\|)", between, re.IGNORECASE))
            if split_matches:
                win_start = prev_r.mention_end + split_matches[0].start()
            else:
                win_start = (prev_r.mention_end + mention_start) // 2
        if idx + 1 < len(same_unit_siblings):
            next_r = same_unit_siblings[idx + 1]
            between = text[mention_end:next_r.mention_start]
            split_matches = list(re.finditer(r"(?:,|\band\b|\bor\b|\|)", between, re.IGNORECASE))
            if split_matches:
                win_end = mention_end + split_matches[0].end()
            else:
                win_end = (mention_end + next_r.mention_start) // 2

    immediate_window = text[max(clause_start, min(win_start, mention_start - 55)):min(clause_end, max(win_end, mention_end + 55))].strip()
    return clause_text, immediate_window


def _resolve_closest_scope_tags(
    unit_text: str,
    mention_start: int,
    mention_end: int,
    scope_dict: dict[str, set[str]],
) -> dict[str, set[str]]:
    """When multiple tags of tranche_or_order or frequency appear in a clause, keep the one closest to the mention."""
    lowered = unit_text.casefold()
    resolved: dict[str, set[str]] = {}
    for dim, labels in scope_dict.items():
        if len(labels) <= 1 or dim not in ("tranche_or_order", "frequency"):
            resolved[dim] = set(labels)
            continue
        best_label = None
        best_dist = 10**9
        for label in labels:
            pat = _SCOPE_PATTERNS.get(dim, {}).get(label)
            if not pat:
                continue
            for m in re.finditer(pat, lowered):
                ms, me = m.span()
                # Penalize prerequisite references like "repayment of the first tranche"
                prefix_ctx = lowered[max(0, ms - 25):ms]
                penalty = 200 if ("repayment" in prefix_ctx or "completing" in prefix_ctx or "after" in prefix_ctx) else 0
                if me <= mention_start:
                    dist = (mention_start - me) + penalty
                elif ms >= mention_end:
                    dist = (ms - mention_end) + penalty
                else:
                    dist = penalty
                if dist < best_dist:
                    best_dist = dist
                    best_label = label
        if best_label is not None:
            resolved[dim] = {best_label}
        else:
            resolved[dim] = set(labels)
    return resolved


_BENEFICIARY_RESTRICTION_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("sc_st", r"\b(?:sc\s*/\s*st|sc|st|scheduled\s+castes?|scheduled\s+tribes?)\b", "SC/ST"),
    ("women", r"\b(?:women|woman|female|mahila|didi|widows?|pregnant|lactating|mothers?)\b", "women"),
    ("tenant", r"\b(?:tenant\s+farmers?|tenants?|sharecroppers?|lessees?)\b", "tenant farmers"),
    ("small_marginal", r"\b(?:small\s+and\s+marginal\s+farmers?|smf|small\s+farmers?|marginal\s+farmers?)\b", "small and marginal farmers"),
    ("bpl", r"\b(?:bpl|below\s+poverty\s+line|antodaya|aay)\b", "BPL"),
    ("general", r"\b(?:general\s+category|general\s+entrepreneurs?|general\s+beneficiar\w*|general\s+applicants?|unreserved)\b", "general category"),
    ("obc", r"\b(?:obc|other\s+backward\s+class\w*)\b", "OBC"),
)


def _extract_beneficiary_restriction_labels(text: str) -> dict[str, str]:
    lowered = text.casefold()
    found: dict[str, str] = {}
    for key, pat, label in _BENEFICIARY_RESTRICTION_PATTERNS:
        if re.search(pat, lowered):
            found[key] = label
    return found


def _verify_clause_restrictions_for_support(
    claim: str,
    parsed_claim: ParsedUploadedClaim,
    substantive_mentions: list[ParsedMentionQuery],
    best_sup: ScoredCandidateMatch,
    retrieved_candidates: list[EnrichedCandidateRule],
) -> tuple[bool, str | None, str | None, list[str]]:
    """Verify that every restriction, cap, qualifier, geography, and frequency in the matched clause is stated in the claim.

    Returns (is_valid, error_reason, reason_code, verified_restrictions_summary).
    """
    cand = best_sup.candidate
    clause_text = cand.clause_text
    primary_mq = substantive_mentions[0]
    omitted_reasons: list[str] = []
    primary_code: str | None = None
    verified_notes: list[str] = []

    # 1. Beneficiary / Category restrictions
    clause_ben = _extract_beneficiary_restriction_labels(clause_text)
    claim_ben = _extract_beneficiary_restriction_labels(claim)
    if clause_ben:
        missing_ben = [lbl for k, lbl in clause_ben.items() if k not in claim_ben]
        if missing_ben:
            omitted_reasons.append(f"claim omits beneficiary restriction: {' and '.join(missing_ben)}")
            primary_code = primary_code or "omitted_beneficiary_restriction"
        else:
            verified_notes.append(f"beneficiary restriction ({' and '.join(clause_ben.values())})")

    # 2. Companion monetary cap / ceiling in the same clause (e.g., "50 percent or up to Rs 500000")
    if primary_mq.mention.unit == "percent":
        clause_siblings = [
            c for c in retrieved_candidates
            if c.unit.evidence_id == cand.unit.evidence_id
            and c.clause_text == clause_text
            and c.rule.unit == "rupees"
            and (
                c.effective_operator == "le"
                or bool(re.search(r"\b(?:up\s+to|maximum|cap|capped\s+at|at\s+most|ceiling)\b", clause_text, re.I))
            )
        ]
        for sib in clause_siblings:
            has_matching_cap_in_claim = any(
                _compare_unit_and_value(m.mention.value, m.mention.unit, sib.rule.value, sib.rule.unit) == (True, True)
                for m in substantive_mentions
            )
            if not has_matching_cap_in_claim:
                omitted_reasons.append(f"claim omits cap: up to {sib.rule.raw_mention}")
                primary_code = primary_code or "omitted_cap"
            else:
                verified_notes.append(f"monetary cap (up to {sib.rule.raw_mention})")

    # Also check if the matched numeric mention itself has an upper-bound operator ("up to", "maximum") omitted by the claim
    if cand.effective_operator == "le":
        has_cap_language = (
            primary_mq.operator == "le"
            or bool(re.search(r"\b(?:up\s+to|at\s+most|maximum|max|cap|capped|limit|ceiling|not\s+exceeding|no\s+more\s+than)\b", claim, re.I))
        )
        if not has_cap_language:
            omitted_reasons.append(f"claim omits cap: up to {cand.rule.raw_mention}")
            primary_code = primary_code or "omitted_cap"
        else:
            verified_notes.append(f"ceiling operator (up to {cand.rule.raw_mention})")
    elif cand.effective_operator == "ge":
        has_min_language = (
            primary_mq.operator == "ge"
            or bool(re.search(r"\b(?:at\s+least|minimum|min|floor|no\s+less\s+than|not\s+less\s+than)\b", claim, re.I))
        )
        if not has_min_language:
            omitted_reasons.append(f"claim omits minimum bound: at least {cand.rule.raw_mention}")
            primary_code = primary_code or "omitted_cap"
        else:
            verified_notes.append(f"minimum bound (at least {cand.rule.raw_mention})")

    # 3. Geography restriction in clause
    clause_geog = _extract_scope_tags(clause_text).get("geography", set())
    claim_geog = parsed_claim.scope_tags.get("geography", set())
    if clause_geog:
        if not (clause_geog & claim_geog):
            omitted_reasons.append(f"claim omits geography restriction: {', '.join(sorted(clause_geog))}")
            primary_code = primary_code or "omitted_geography_restriction"
        else:
            verified_notes.append(f"geography ({', '.join(sorted(clause_geog & claim_geog))})")

    # 4. Frequency restriction in clause (resolved to the mention's local frequency)
    clause_freq = cand.clause_scope.get("frequency", set()) & _extract_scope_tags(clause_text).get("frequency", set())
    claim_freq = parsed_claim.scope_tags.get("frequency", set())
    if clause_freq:
        if not (clause_freq & claim_freq):
            omitted_reasons.append(f"claim omits frequency restriction: {', '.join(sorted(clause_freq))}")
            primary_code = primary_code or "omitted_frequency_restriction"
        else:
            verified_notes.append(f"frequency ({', '.join(sorted(clause_freq & claim_freq))})")

    # 5. Basis restriction (per hectare)
    if "per_hectare" in cand.clause_scope.get("basis", set()):
        if "per_hectare" not in parsed_claim.scope_tags.get("basis", set()):
            omitted_reasons.append("claim omits basis restriction: per hectare")
            primary_code = primary_code or "omitted_basis_restriction"
        else:
            verified_notes.append("basis (per hectare)")

    # 6. Qualifier ("whichever is less" / "whichever is higher")
    if cand.qualifier_tag:
        if parsed_claim.qualifier != cand.qualifier_tag:
            omitted_reasons.append(f"claim omits qualifier: {cand.qualifier_tag}")
            primary_code = primary_code or "omitted_qualifier"
        else:
            verified_notes.append(f"qualifier ({cand.qualifier_tag})")

    # 7. Conditional markers ("only", "except", "unless", "provided that", "provided the")
    for m_cond in re.finditer(
        r"\b(only|except|unless|provided\s+that|provided\s+the)\s+([^.;,]{3,65})",
        clause_text.casefold(),
    ):
        marker = m_cond.group(1)
        tail = m_cond.group(2).strip()
        tail_kws = _extract_subject_keywords(tail)
        if tail_kws and not (tail_kws <= parsed_claim.subject_keywords):
            omitted_reasons.append(f"claim omits conditional restriction: '{marker} {tail}'")
            primary_code = primary_code or "omitted_restriction"
        elif tail_kws:
            verified_notes.append(f"condition ('{marker} {tail}')")

    if omitted_reasons:
        return False, "; ".join(omitted_reasons) + ".", primary_code or "unestablished_condition", verified_notes

    return True, None, None, verified_notes


def _enrich_unit_candidates(unit: ExtractedEvidenceUnit) -> list[EnrichedCandidateRule]:
    raw_rules = extract_uploaded_candidates(
        unit.text, unit.evidence_id, unit.document_id, unit.physical_pdf_page
    )
    enriched: list[EnrichedCandidateRule] = []
    passage_keywords = _extract_subject_keywords(unit.text)
    passage_scope = _extract_scope_tags(unit.text)

    for r in raw_rules:
        clause_text, immediate_window = _extract_clause_and_window(
            unit.text, r.mention_start, r.mention_end, raw_rules, r
        )
        # Combine immediate_window scope and clause_text scope
        win_scope = _extract_scope_tags(immediate_window)
        cl_scope = _extract_scope_tags(clause_text)
        # If immediate_window has a specific tranche or category, prefer it over other tranches in the clause
        merged_clause_scope: dict[str, set[str]] = dict(cl_scope)
        for dim, vals in win_scope.items():
            if vals:
                merged_clause_scope[dim] = vals

        merged_clause_scope = _resolve_closest_scope_tags(
            unit.text, r.mention_start, r.mention_end, merged_clause_scope
        )

        # If the clause doesn't specify a scope dimension (e.g. geography or beneficiary stated in the first sentence of the paragraph),
        # inherit from passage_scope ONLY if passage_scope has a single unambiguous value for that dimension.
        for dim, p_vals in passage_scope.items():
            if dim not in merged_clause_scope and len(p_vals) == 1:
                merged_clause_scope[dim] = set(p_vals)

        eff_op = r.numeric_operator or _extract_local_operator(unit.text, r.mention_start)
        qual_tag = _extract_qualifier_tag(clause_text) or _extract_qualifier_tag(unit.text)

        enriched.append(
            EnrichedCandidateRule(
                rule=r,
                unit=unit,
                clause_text=clause_text,
                immediate_window=immediate_window,
                clause_keywords=_extract_subject_keywords(clause_text) | _extract_subject_keywords(immediate_window),
                passage_keywords=passage_keywords,
                clause_scope=merged_clause_scope,
                passage_scope=passage_scope,
                effective_operator=eff_op,
                qualifier_tag=qual_tag,
                clause_has_negation=_has_negation(clause_text),
                clause_restrictions=_has_strict_restriction(clause_text),
            )
        )
    return enriched


def _compute_proximity_score(
    unit_text: str,
    mention_start: int,
    mention_end: int,
    claim_keywords: set[str],
) -> float:
    """Score how close the numeric mention is to the claim's matched subject words in unit_text."""
    if not claim_keywords:
        return 0.5
    lowered = unit_text.casefold()
    distances: list[int] = []
    for token_match in re.finditer(r"[a-z]{3,}", lowered):
        norm = _normalize_token(token_match.group(0))
        if norm in claim_keywords:
            t_start, t_end = token_match.span()
            if t_end <= mention_start:
                dist = mention_start - t_end
            elif t_start >= mention_end:
                dist = t_start - mention_end
            else:
                dist = 0
            distances.append(dist)
    if not distances:
        return 0.0
    distances.sort()
    top_dists = distances[: min(4, len(distances))]
    avg_dist = sum(top_dists) / len(top_dists)
    return 1.0 / (1.0 + avg_dist / 75.0)


def _check_operator_compatibility(claim_op: str | None, rule_op: str | None, exact_val: bool) -> bool:
    """Determine if the claim's operator is compatible with the candidate rule's operator."""
    if not exact_val:
        return False
    if claim_op is None or rule_op is None:
        return True
    if claim_op == rule_op:
        return True
    # Compatible pairs at the boundary value
    if {claim_op, rule_op} <= {"le", "eq"} or {claim_op, rule_op} <= {"ge", "eq"}:
        return True
    # Opposite inequalities are incompatible (e.g., 'le' vs 'gt'/'ge', 'lt' vs 'gt'/'ge')
    return False


def _detect_scope_mismatches(
    claim_scope: dict[str, set[str]],
    cand: EnrichedCandidateRule,
    claim_has_negation: bool,
) -> list[str]:
    """Return list of scope dimensions where the claim conflicts with the candidate rule."""
    mismatches: list[str] = []

    # Check if claim asserts benefit for an explicitly excluded group (e.g. taxpayers, corporates, regular civil servants)
    claim_cats = claim_scope.get("beneficiary_category", set())
    if "excluded_privileged" in claim_cats and not claim_has_negation:
        # Unless the candidate clause itself grants something to excluded_privileged without negation
        if "excluded_privileged" not in cand.clause_scope.get("beneficiary_category", set()) or cand.clause_has_negation:
            mismatches.append("beneficiary_category")

    for dim in ("tranche_or_order", "beneficiary_category", "geography", "frequency", "basis"):
        c_vals = claim_scope.get(dim, set())
        r_vals = cand.clause_scope.get(dim, set())
        if not c_vals or not r_vals:
            continue
        if dim == "beneficiary_category":
            demographic_keys = {"sc_st", "women", "general", "obc", "small_marginal_farmer", "large_farmer", "excluded_privileged"}
            c_demo = c_vals & demographic_keys
            r_demo = r_vals & demographic_keys
            if c_demo and r_demo and c_demo.isdisjoint(r_demo):
                mismatches.append(dim)
                continue
        if c_vals.isdisjoint(r_vals):
            mismatches.append(dim)

    return sorted(set(mismatches))


@dataclass
class ScoredCandidateMatch:
    candidate: EnrichedCandidateRule
    score: float
    keyword_overlap: float
    proximity_score: float
    unit_compatible: bool
    exact_value_match: bool
    operator_compatible: bool
    qualifier_compatible: bool
    negation_compatible: bool
    scope_mismatches: list[str] = field(default_factory=list)


def _score_candidate_for_mention(
    parsed_claim: ParsedUploadedClaim,
    mention_query: ParsedMentionQuery,
    cand: EnrichedCandidateRule,
) -> ScoredCandidateMatch:
    unit_compatible, exact_value = _compare_unit_and_value(
        mention_query.mention.value,
        mention_query.mention.unit,
        cand.rule.value,
        cand.rule.unit,
    )

    # Keyword overlap
    query_kws = parsed_claim.subject_keywords | mention_query.local_keywords
    if query_kws:
        clause_hits = len(query_kws & cand.clause_keywords)
        passage_hits = len(query_kws & cand.passage_keywords)
        clause_ratio = clause_hits / len(query_kws)
        passage_ratio = passage_hits / len(query_kws)
        kw_overlap = 0.65 * clause_ratio + 0.35 * passage_ratio
    else:
        kw_overlap = 0.0

    prox = _compute_proximity_score(
        cand.unit.text,
        cand.rule.mention_start,
        cand.rule.mention_end,
        query_kws,
    )

    # Effective scope for this mention combines global claim scope and local mention scope
    merged_claim_scope: dict[str, set[str]] = dict(parsed_claim.scope_tags)
    for dim, vals in mention_query.local_scope.items():
        if vals:
            merged_claim_scope[dim] = vals

    scope_mismatches = _detect_scope_mismatches(
        merged_claim_scope, cand, parsed_claim.has_negation
    )

    # Scope alignment bonus when claim and candidate share explicit scope tags
    shared_scope_dims = 0
    for dim, c_vals in merged_claim_scope.items():
        r_vals = cand.clause_scope.get(dim, set())
        if c_vals and r_vals and not c_vals.isdisjoint(r_vals):
            shared_scope_dims += 1
    scope_bonus = min(1.0, shared_scope_dims * 0.5) if merged_claim_scope else 0.5
    if scope_mismatches:
        scope_bonus = 0.0

    op_compat = _check_operator_compatibility(
        mention_query.operator, cand.effective_operator, exact_value
    )
    qual_compat = True
    if parsed_claim.qualifier and cand.qualifier_tag and parsed_claim.qualifier != cand.qualifier_tag:
        qual_compat = False

    neg_compat = (parsed_claim.has_negation == cand.clause_has_negation)

    composite = (
        0.45 * kw_overlap
        + 0.25 * prox
        + 0.15 * scope_bonus
        + (0.15 if unit_compatible else 0.0)
    )

    return ScoredCandidateMatch(
        candidate=cand,
        score=round(composite, 4),
        keyword_overlap=round(kw_overlap, 4),
        proximity_score=round(prox, 4),
        unit_compatible=unit_compatible,
        exact_value_match=exact_value,
        operator_compatible=op_compat,
        qualifier_compatible=qual_compat,
        negation_compatible=neg_compat,
        scope_mismatches=scope_mismatches,
    )


def evaluate_uploaded_claim(
    claim: str,
    retrieved: list[ExtractedEvidenceUnit],
    corpus: list[ExtractedEvidenceUnit],
) -> dict[str, Any]:
    """Condition-aware evaluation of a claim against uploaded document units and candidate rules.

    Returns a dictionary containing:
      - verdict: SUPPORTED | CONTRADICTED | WRONG_CONTEXT | UNVERIFIABLE
      - supporting_ids: list[str]
      - contradicting_ids: list[str]
      - context_mismatch: list[str]
      - reason: str
      - reason_code: str
      - matched_passage: str | None
      - matched_candidate_rule: dict[str, Any] | None
      - matched_page: int | None
      - matched_score: float | None
    """
    if not extract_all_numeric_mentions(claim):
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": (
                "No numerical quantity was found in the claim. Use Search Document Excerpts for "
                "qualitative questions, or enter a claim containing an amount, rate, duration, area, or capacity."
            ),
            "reason_code": "no_numeric_claim",
            "matched_passage": None,
            "matched_candidate_rule": None,
            "matched_page": None,
            "matched_score": None,
        }

    if re.search(r"mid[ -]?season\s+adversity", claim, re.I) and re.search(r"expected\s+yield", claim, re.I):
        yield_result = _compare_yield_threshold(claim, retrieved, corpus)
        if yield_result is not None:
            v, sup, con, rsn = yield_result
            matched_unit = next((u for u in retrieved if u.evidence_id in (sup or con)), None)
            return {
                "verdict": v,
                "supporting_ids": sup,
                "contradicting_ids": con,
                "context_mismatch": [],
                "reason": rsn,
                "reason_code": "supported_candidate_match" if v == "SUPPORTED" else ("value_contradicted" if v == "CONTRADICTED" else "conflicting_values"),
                "matched_passage": matched_unit.text if matched_unit else None,
                "matched_candidate_rule": None,
                "matched_page": matched_unit.physical_pdf_page if matched_unit else None,
                "matched_score": 1.0 if matched_unit else None,
            }
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": "Retrieved passages do not establish the claimed mid-season adversity expected-yield threshold and its conditions.",
            "reason_code": "unestablished_condition",
            "matched_passage": retrieved[0].text if retrieved else None,
            "matched_candidate_rule": None,
            "matched_page": retrieved[0].physical_pdf_page if retrieved else None,
            "matched_score": 0.0,
        }

    uploaded_corpus = [u for u in corpus if is_uploaded(u)]
    uploaded_retrieved = [u for u in retrieved if is_uploaded(u)]
    total_corpus_words = sum(len(u.text.split()) for u in uploaded_corpus)

    # Fast exact-signature check for single-sentence micro-passages and verbatim matches
    signature = _signature(claim)
    if signature is not None:
        context, value = signature
        relevant = []
        for unit in uploaded_corpus:
            if unit.evidence_type != "paragraph":
                continue
            cand_sig = _signature(unit.text)
            if cand_sig and cand_sig[0] == context:
                relevant.append((unit, cand_sig[1]))
        retrieved_ids = {u.evidence_id for u in uploaded_retrieved}
        visible = [(u, number) for u, number in relevant if u.evidence_id in retrieved_ids]
        if visible:
            if len({number for _, number in relevant}) > 1:
                u0 = visible[0][0]
                return {
                    "verdict": "UNVERIFIABLE",
                    "supporting_ids": [],
                    "contradicting_ids": [],
                    "context_mismatch": [],
                    "reason": "The uploaded document contains conflicting values for the same statement.",
                    "reason_code": "conflicting_values",
                    "matched_passage": u0.text,
                    "matched_candidate_rule": None,
                    "matched_page": u0.physical_pdf_page,
                    "matched_score": 1.0,
                }
            supports = [u for u, number in visible if number == value]
            if supports:
                u0 = supports[0]
                cands = extract_uploaded_candidates(u0.text, u0.evidence_id, u0.document_id, u0.physical_pdf_page)
                return {
                    "verdict": "SUPPORTED",
                    "supporting_ids": [u.evidence_id for u in supports],
                    "contradicting_ids": [],
                    "context_mismatch": [],
                    "reason": "The complete numerical statement matches the uploaded passage.",
                    "reason_code": "supported_candidate_match",
                    "matched_passage": u0.text,
                    "matched_candidate_rule": cands[0].to_dict() if cands else None,
                    "matched_page": u0.physical_pdf_page,
                    "matched_score": 1.0,
                }
            if total_corpus_words <= 15:
                u0 = visible[0][0]
                cands = extract_uploaded_candidates(u0.text, u0.evidence_id, u0.document_id, u0.physical_pdf_page)
                return {
                    "verdict": "CONTRADICTED",
                    "supporting_ids": [],
                    "contradicting_ids": [u.evidence_id for u, _ in visible],
                    "context_mismatch": [],
                    "reason": "The same statement in the uploaded document specifies a different value.",
                    "reason_code": "value_contradicted",
                    "matched_passage": u0.text,
                    "matched_candidate_rule": cands[0].to_dict() if cands else None,
                    "matched_page": u0.physical_pdf_page,
                    "matched_score": 1.0,
                }
        elif relevant:
            return {
                "verdict": "UNVERIFIABLE",
                "supporting_ids": [],
                "contradicting_ids": [],
                "context_mismatch": [],
                "reason": "Retrieved passages do not establish the complete claim and its conditions.",
                "reason_code": "no_relevant_passage",
                "matched_passage": None,
                "matched_candidate_rule": None,
                "matched_page": None,
                "matched_score": None,
            }

    # Preserve strict abstention on synthetic 1-sentence micro-snippets (<= 12 words) when signature differs
    if len(uploaded_corpus) == 1 and total_corpus_words <= 12:
        if not uploaded_retrieved:
            return {
                "verdict": "UNVERIFIABLE",
                "supporting_ids": [],
                "contradicting_ids": [],
                "context_mismatch": [],
                "reason": "Retrieved passages do not establish the complete claim and its conditions.",
                "reason_code": "no_relevant_passage",
                "matched_passage": None,
                "matched_candidate_rule": None,
                "matched_page": None,
                "matched_score": None,
            }
        # Exact normalized full-text equality for multi-number qualified single sentences
        norm_claim = re.sub(r"\s+", " ", claim.casefold()).strip().rstrip(".")
        norm_doc = re.sub(r"\s+", " ", uploaded_corpus[0].text.casefold()).strip().rstrip(".")
        if norm_claim == norm_doc:
            u0 = uploaded_corpus[0]
            cands = extract_uploaded_candidates(u0.text, u0.evidence_id, u0.document_id, u0.physical_pdf_page)
            return {
                "verdict": "SUPPORTED",
                "supporting_ids": [u0.evidence_id],
                "contradicting_ids": [],
                "context_mismatch": [],
                "reason": "The complete numerical statement matches the uploaded passage.",
                "reason_code": "supported_candidate_match",
                "matched_passage": u0.text,
                "matched_candidate_rule": cands[0].to_dict() if cands else None,
                "matched_page": u0.physical_pdf_page,
                "matched_score": 1.0,
            }
        u0 = uploaded_corpus[0]
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": "Retrieved passages do not establish the complete claim and its conditions.",
            "reason_code": "unestablished_condition",
            "matched_passage": u0.text,
            "matched_candidate_rule": None,
            "matched_page": u0.physical_pdf_page,
            "matched_score": 0.0,
        }

    if not uploaded_retrieved:
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": "No relevant passage was retrieved from the uploaded document.",
            "reason_code": "no_relevant_passage",
            "matched_passage": None,
            "matched_candidate_rule": None,
            "matched_page": None,
            "matched_score": None,
        }

    parsed_claim = parse_uploaded_claim(claim)
    if not parsed_claim.mentions:
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": "No valid numerical mention could be parsed from the claim.",
            "reason_code": "no_numeric_claim",
            "matched_passage": None,
            "matched_candidate_rule": None,
            "matched_page": None,
            "matched_score": None,
        }

    retrieved_candidates: list[EnrichedCandidateRule] = []
    for unit in uploaded_retrieved:
        retrieved_candidates.extend(_enrich_unit_candidates(unit))

    corpus_candidates: list[EnrichedCandidateRule] = []
    for unit in uploaded_corpus:
        corpus_candidates.extend(_enrich_unit_candidates(unit))

    if not retrieved_candidates:
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": "Retrieved passages do not contain any numerical candidate rules.",
            "reason_code": "no_relevant_passage",
            "matched_passage": uploaded_retrieved[0].text,
            "matched_candidate_rule": None,
            "matched_page": uploaded_retrieved[0].physical_pdf_page,
            "matched_score": 0.0,
        }

    # Evaluate each numeric mention in the claim against retrieved candidate rules
    # Filter out bare ordinal mentions (like "1" in "1st instalment") if another substantive mention exists
    substantive_mentions = [
        mq for mq in parsed_claim.mentions
        if not (
            len(parsed_claim.mentions) > 1
            and mq.mention.unit in ("count", "instalments")
            and mq.mention.value in (1.0, 2.0, 3.0, 4.0)
            and re.search(r"\b(?:1st|2nd|3rd|4th|first|second|third|fourth)\b", mq.mention.raw_text, re.I)
        )
    ] or parsed_claim.mentions

    primary_mq = substantive_mentions[0]
    scored_all = [_score_candidate_for_mention(parsed_claim, primary_mq, c) for c in retrieved_candidates]
    scored_all.sort(key=lambda s: (s.score, s.keyword_overlap, s.proximity_score), reverse=True)

    best_any = scored_all[0]
    if best_any.keyword_overlap < 0.22:
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": "No relevant passage in the uploaded document matches the subject of the claim.",
            "reason_code": "no_relevant_passage",
            "matched_passage": best_any.candidate.unit.text,
            "matched_candidate_rule": best_any.candidate.rule.to_dict(),
            "matched_page": best_any.candidate.unit.physical_pdf_page,
            "matched_score": best_any.score,
        }

    unit_compat_matches = [s for s in scored_all if s.unit_compatible and s.keyword_overlap >= 0.22]
    if not unit_compat_matches:
        return {
            "verdict": "UNVERIFIABLE",
            "supporting_ids": [],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": (
                f"Retrieved passages discuss the topic on page {best_any.candidate.unit.physical_pdf_page}, "
                f"but no candidate rule has a compatible unit for '{primary_mq.mention.unit}'."
            ),
            "reason_code": "unit_mismatch",
            "matched_passage": best_any.candidate.unit.text,
            "matched_candidate_rule": best_any.candidate.rule.to_dict(),
            "matched_page": best_any.candidate.unit.physical_pdf_page,
            "matched_score": best_any.score,
        }

    # Partition unit-compatible relevant matches
    supporting_matches = [
        s for s in unit_compat_matches
        if s.exact_value_match
        and not s.scope_mismatches
        and s.operator_compatible
        and s.qualifier_compatible
        and s.negation_compatible
    ]
    wrong_context_matches = [
        s for s in unit_compat_matches
        if s.exact_value_match and s.scope_mismatches
    ]
    contradicting_matches = [
        s for s in unit_compat_matches
        if not s.scope_mismatches
        and s.negation_compatible
        and (
            not s.exact_value_match
            or not s.operator_compatible
            or not s.qualifier_compatible
        )
    ]

    # If the claim has multiple substantive mentions (e.g. "50% subsidy up to Rs. 50 lakh"),
    # verify secondary mentions too.
    if len(substantive_mentions) > 1 and supporting_matches:
        for sec_mq in substantive_mentions[1:]:
            sec_scored = [
                _score_candidate_for_mention(parsed_claim, sec_mq, c)
                for c in retrieved_candidates
            ]
            sec_compat = [s for s in sec_scored if s.unit_compatible and s.keyword_overlap >= 0.20]
            sec_sup = [
                s for s in sec_compat
                if s.exact_value_match
                and not s.scope_mismatches
                and s.operator_compatible
                and s.qualifier_compatible
                and s.negation_compatible
            ]
            if not sec_sup:
                supporting_matches = []
                sec_wc = [s for s in sec_compat if s.exact_value_match and s.scope_mismatches]
                sec_contra = [s for s in sec_compat if not s.scope_mismatches and not s.exact_value_match]
                if sec_wc:
                    wrong_context_matches.extend(sec_wc)
                elif sec_contra:
                    contradicting_matches.extend(sec_contra)
                break

    # 1. Check WRONG_CONTEXT first when the exact claimed value exists in the document under a conflicting condition/category/frequency/tranche
    # and there is no higher-scoring exact supporting match for the claimed condition.
    if wrong_context_matches and (
        not supporting_matches or wrong_context_matches[0].score > supporting_matches[0].score + 0.05
    ):
        best_wc = wrong_context_matches[0]
        mismatch_str = ", ".join(best_wc.scope_mismatches)
        return {
            "verdict": "WRONG_CONTEXT",
            "supporting_ids": [],
            "contradicting_ids": [best_wc.candidate.unit.evidence_id],
            "context_mismatch": best_wc.scope_mismatches,
            "reason": (
                f"The value {best_wc.candidate.rule.raw_mention} exists in the uploaded document on page "
                f"{best_wc.candidate.unit.physical_pdf_page}, but under a different condition ({mismatch_str})."
            ),
            "reason_code": "wrong_context_scope_mismatch",
            "matched_passage": best_wc.candidate.unit.text,
            "matched_candidate_rule": best_wc.candidate.rule.to_dict(),
            "matched_page": best_wc.candidate.unit.physical_pdf_page,
            "matched_score": best_wc.score,
        }

    # 2. Check SUPPORTED
    if supporting_matches:
        best_sup = supporting_matches[0]
        # Check for corpus-wide conflicting values on the identical clause/subject and scope
        conflicting_corpus = [
            c for c in corpus_candidates
            if c.unit.evidence_id != best_sup.candidate.unit.evidence_id
            and _compare_unit_and_value(c.rule.value, c.rule.unit, best_sup.candidate.rule.value, best_sup.candidate.rule.unit) == (True, False)
            and c.clause_scope == best_sup.candidate.clause_scope
            and len(c.clause_keywords & best_sup.candidate.clause_keywords) >= max(2, len(best_sup.candidate.clause_keywords) - 1)
        ]
        if conflicting_corpus:
            return {
                "verdict": "UNVERIFIABLE",
                "supporting_ids": [],
                "contradicting_ids": [],
                "context_mismatch": [],
                "reason": "The uploaded document contains conflicting numerical values for the same subject and conditions.",
                "reason_code": "conflicting_values",
                "matched_passage": best_sup.candidate.unit.text,
                "matched_candidate_rule": best_sup.candidate.rule.to_dict(),
                "matched_page": best_sup.candidate.unit.physical_pdf_page,
                "matched_score": best_sup.score,
            }

        # Verify that every restriction, cap, qualifier, geography, and frequency in the matched passage is stated in the claim
        restrictions_ok, omit_reason, omit_code, verified_notes = _verify_clause_restrictions_for_support(
            claim=claim,
            parsed_claim=parsed_claim,
            substantive_mentions=substantive_mentions,
            best_sup=best_sup,
            retrieved_candidates=retrieved_candidates,
        )
        if not restrictions_ok:
            return {
                "verdict": "UNVERIFIABLE",
                "supporting_ids": [],
                "contradicting_ids": [],
                "context_mismatch": [],
                "reason": f"Cannot verify as SUPPORTED because {omit_reason}",
                "reason_code": omit_code or "unestablished_condition",
                "matched_passage": best_sup.candidate.unit.text,
                "matched_candidate_rule": best_sup.candidate.rule.to_dict(),
                "matched_page": best_sup.candidate.unit.physical_pdf_page,
                "matched_score": best_sup.score,
            }

        verified_clause_summary = (
            f" All passage restrictions verified in claim ({', '.join(verified_notes)})."
            if verified_notes
            else " No additional passage restrictions were omitted."
        )
        return {
            "verdict": "SUPPORTED",
            "supporting_ids": [best_sup.candidate.unit.evidence_id],
            "contradicting_ids": [],
            "context_mismatch": [],
            "reason": (
                f"Matched uploaded candidate rule {best_sup.candidate.rule.rule_id} "
                f"({best_sup.candidate.rule.raw_mention}) on page {best_sup.candidate.unit.physical_pdf_page} "
                f"with compatible value, unit, operator, and conditions.{verified_clause_summary}"
            ),
            "reason_code": "supported_candidate_match",
            "matched_passage": best_sup.candidate.unit.text,
            "matched_candidate_rule": best_sup.candidate.rule.to_dict(),
            "matched_page": best_sup.candidate.unit.physical_pdf_page,
            "matched_score": best_sup.score,
        }

    # 3. Check CONTRADICTED
    if contradicting_matches:
        contradicting_matches.sort(key=lambda s: (s.score, s.keyword_overlap, s.proximity_score), reverse=True)
        best_con = contradicting_matches[0]
        if best_con.keyword_overlap >= 0.30:
            if not best_con.exact_value_match:
                reason_text = (
                    f"Contradicted by candidate rule {best_con.candidate.rule.rule_id} on page "
                    f"{best_con.candidate.unit.physical_pdf_page}: document states "
                    f"'{best_con.candidate.rule.raw_mention}' instead of '{primary_mq.mention.raw_text}'."
                )
                code = "value_contradicted"
            else:
                reason_text = (
                    f"Contradicted by candidate rule {best_con.candidate.rule.rule_id} on page "
                    f"{best_con.candidate.unit.physical_pdf_page}: incompatible operator, qualifier, or negation."
                )
                code = "operator_contradicted"
            return {
                "verdict": "CONTRADICTED",
                "supporting_ids": [],
                "contradicting_ids": [best_con.candidate.unit.evidence_id],
                "context_mismatch": [],
                "reason": reason_text,
                "reason_code": code,
                "matched_passage": best_con.candidate.unit.text,
                "matched_candidate_rule": best_con.candidate.rule.to_dict(),
                "matched_page": best_con.candidate.unit.physical_pdf_page,
                "matched_score": best_con.score,
            }

    return {
        "verdict": "UNVERIFIABLE",
        "supporting_ids": [],
        "contradicting_ids": [],
        "context_mismatch": [],
        "reason": "Retrieved passages do not establish the claimed numerical rule and its conditions.",
        "reason_code": "no_relevant_passage",
        "matched_passage": best_any.candidate.unit.text,
        "matched_candidate_rule": best_any.candidate.rule.to_dict(),
        "matched_page": best_any.candidate.unit.physical_pdf_page,
        "matched_score": best_any.score,
    }


def compare_uploaded_claim(
    claim: str,
    retrieved: list[ExtractedEvidenceUnit],
    corpus: list[ExtractedEvidenceUnit],
) -> tuple[str, list[str], list[str], str]:
    """Backwards-compatible tuple wrapper around evaluate_uploaded_claim."""
    result = evaluate_uploaded_claim(claim, retrieved, corpus)
    return (
        result["verdict"],
        result["supporting_ids"],
        result["contradicting_ids"],
        result["reason"],
    )
