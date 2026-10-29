"""Optional LLM-based structured claim parser with strict JSON schema validation (Phase 10)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import requests

from fieldguard.claim_parser import (
    REQUIRED_PARSED_CLAIM_FIELDS,
    DeterministicClaimParser,
    ParsedClaim,
    validate_parsed_claim_schema,
)
from fieldguard.numeric_normalizer import normalize_claim_numerics

ALLOWED_SCHEMES = {"PMFBY", "RWBCIS", "PM_KISAN", "NAIS", None}
ALLOWED_OPERATORS = {"le", "ge", "lt", "gt", "eq", None}
ALLOWED_SEASONS = {"kharif", "rabi", "annual", "zaid_summer", None}
ALLOWED_CROP_CATEGORIES = {
    "food_grain_and_oilseed",
    "commercial_and_horticultural",
    "unirrigated_crops",
    "irrigated_crops",
    "all_notified_crops",
    "perennial_betelvine_pilot",
    "wild_animal_attack_addon",
    "non_covered_livestock_aquaculture",
    None,
}


@dataclass
class LLMParserConfig:
    """Configuration for the optional LLM-based claim parser."""

    provider: str = ""
    model: str = ""
    endpoint: str = ""
    api_key: str = ""
    timeout_sec: float = 30.0
    max_retries: int = 2
    temperature: float = 0.0
    max_tokens: int = 512
    prompt_version: str = "v1.0"
    schema_version: str = "1.0.0"
    cache_path: Path | None = None

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> LLMParserConfig:
        if project_root is None:
            project_root = Path(__file__).resolve().parents[2]
        return cls(
            provider=os.environ.get("FIELDGUARD_LLM_PROVIDER", "").strip(),
            model=os.environ.get("FIELDGUARD_LLM_MODEL", "").strip(),
            endpoint=os.environ.get("FIELDGUARD_LLM_ENDPOINT", "").strip(),
            api_key=os.environ.get("FIELDGUARD_LLM_API_KEY", "").strip(),
            timeout_sec=float(os.environ.get("FIELDGUARD_LLM_TIMEOUT_SEC", "30.0")),
            max_retries=int(os.environ.get("FIELDGUARD_LLM_MAX_RETRIES", "2")),
            temperature=float(os.environ.get("FIELDGUARD_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.environ.get("FIELDGUARD_LLM_MAX_TOKENS", "512")),
            cache_path=project_root / "cache" / "parser" / "llm_parser_cache.json",
        )

    def is_configured(self) -> bool:
        return bool(self.provider and self.model and (self.api_key or self.endpoint))


@dataclass
class LLMParseDiagnostics:
    """Diagnostics for a single LLM parse call (schema validity, unsupported inference, cost)."""

    schema_valid: bool
    parse_failed: bool
    unsupported_inference_detected: bool
    unsupported_inferred_fields: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_llm_extraction_prompt(question: str, candidate_claim: str) -> str:
    """
    Construct the system/user prompt instructing the LLM to extract ONLY explicit structured
    claim fields into strict JSON without inferring missing conditions or assigning a verdict.
    """
    return (
        "You are a strict structured claim extraction module for FieldGuard.\n"
        "Extract ONLY explicitly stated fields from the Question and Candidate Claim below.\n"
        "Do NOT infer or invent missing crop categories, seasons, dates, units, or qualifications.\n"
        "Do NOT output a verification verdict.\n"
        "Return a single JSON object containing exactly:\n"
        "  scheme, claimed_value, claimed_unit, numeric_operator, crop_category, season,\n"
        "  qualification, requested_policy_version, requested_effective_date,\n"
        "  parse_status, uncertain_fields.\n\n"
        f"Question: {question}\n"
        f"Candidate Claim: {candidate_claim}\n"
    )


def detect_unsupported_llm_inferences(
    parsed_dict: dict[str, Any],
    question: str,
    candidate_claim: str,
) -> list[str]:
    """
    Check whether an LLM output invented fields not present in the input text
    (e.g., inventing a requested_effective_date, season, or crop_category when omitted).
    """
    combined = f"{question or ''} {candidate_claim or ''}".lower()
    inferred: list[str] = []

    eff_date = parsed_dict.get("requested_effective_date")
    if eff_date is not None:
        if str(eff_date).lower() not in combined and not any(
            yr in combined for yr in ("2017", "2018")
        ):
            inferred.append("requested_effective_date")

    season = parsed_dict.get("season")
    if season in ("kharif", "rabi", "zaid_summer"):
        if season.split("_")[0] not in combined:
            inferred.append("season")

    crop_cat = parsed_dict.get("crop_category")
    if crop_cat == "food_grain_and_oilseed":
        if not re.search(
            r"food|grain|oilseed|cereal|millet|pulse|paddy|wheat|mustard|soybean|groundnut|gram|lentil|bajra|sorghum|maize",
            combined,
        ):
            inferred.append("crop_category")
    elif crop_cat == "commercial_and_horticultural":
        if not re.search(
            r"commercial|horticultur|cotton|sugarcane|jute|potato|onion|banana|chilli|ginger|turmeric|spice",
            combined,
        ):
            inferred.append("crop_category")

    return inferred


def validate_and_sanitize_llm_output(
    raw_response_text: str,
    question: str,
    candidate_claim: str,
) -> tuple[ParsedClaim, LLMParseDiagnostics]:
    """
    Parse and strictly validate raw LLM JSON output.
    If JSON is malformed, violates schema, or attempts to bypass verification,
    returns a safe failed_malformed ParsedClaim that will cause the verifier to abstain.
    """
    det_helper = DeterministicClaimParser()
    det_ref = det_helper.parse(question, candidate_claim)

    try:
        cleaned = raw_response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()
        payload = json.loads(cleaned)
    except Exception as exc:
        return (
            ParsedClaim(
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
                uncertain_fields=list(REQUIRED_PARSED_CLAIM_FIELDS),
                raw_question=question,
                raw_claim=candidate_claim,
                parser_name="llm_claim_parser_failed",
            ),
            LLMParseDiagnostics(
                schema_valid=False,
                parse_failed=True,
                unsupported_inference_detected=False,
                error_message=f"Invalid JSON: {exc}",
            ),
        )

    if not isinstance(payload, dict):
        return (
            ParsedClaim(
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
                uncertain_fields=list(REQUIRED_PARSED_CLAIM_FIELDS),
                raw_question=question,
                raw_claim=candidate_claim,
                parser_name="llm_claim_parser_failed",
            ),
            LLMParseDiagnostics(
                schema_valid=False,
                parse_failed=True,
                unsupported_inference_detected=False,
                error_message="JSON root must be an object",
            ),
        )

    # Ensure required fields and check enum validity
    valid_schema, schema_errs = validate_parsed_claim_schema(payload)
    if payload.get("scheme") not in ALLOWED_SCHEMES:
        valid_schema = False
        schema_errs.append(f"Invalid scheme: {payload.get('scheme')}")
    if payload.get("numeric_operator") not in ALLOWED_OPERATORS:
        valid_schema = False
        schema_errs.append(f"Invalid numeric_operator: {payload.get('numeric_operator')}")
    if payload.get("season") not in ALLOWED_SEASONS:
        valid_schema = False
        schema_errs.append(f"Invalid season: {payload.get('season')}")
    if payload.get("crop_category") not in ALLOWED_CROP_CATEGORIES:
        valid_schema = False
        schema_errs.append(f"Invalid crop_category: {payload.get('crop_category')}")

    if not valid_schema:
        return (
            ParsedClaim(
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
                uncertain_fields=list(REQUIRED_PARSED_CLAIM_FIELDS),
                raw_question=question,
                raw_claim=candidate_claim,
                parser_name="llm_claim_parser_failed",
            ),
            LLMParseDiagnostics(
                schema_valid=False,
                parse_failed=True,
                unsupported_inference_detected=False,
                error_message="; ".join(schema_errs),
            ),
        )

    inferred_fields = detect_unsupported_llm_inferences(payload, question, candidate_claim)
    uncertain = list(payload.get("uncertain_fields") or [])
    for inf_f in inferred_fields:
        # Nullify unsupported inferred fields and mark them uncertain
        payload[inf_f] = None
        if inf_f not in uncertain:
            uncertain.append(inf_f)

    c_val = float(payload["claimed_value"]) if payload.get("claimed_value") is not None else None
    c_unit = payload.get("claimed_unit")
    num_expr = normalize_claim_numerics(f"{question} {candidate_claim}")

    status = payload.get("parse_status", "success")
    if c_val is None or c_unit is None:
        status = "failed_malformed"
    elif uncertain:
        status = "partial_uncertain"

    parsed = ParsedClaim(
        scheme=payload.get("scheme"),
        claimed_value=c_val,
        claimed_unit=c_unit,
        numeric_operator=payload.get("numeric_operator"),
        crop_category=payload.get("crop_category"),
        season=payload.get("season"),
        qualification=payload.get("qualification"),
        requested_policy_version=payload.get("requested_policy_version"),
        requested_effective_date=payload.get("requested_effective_date"),
        parse_status=status,
        uncertain_fields=uncertain,
        rule_parameter=payload.get("rule_parameter") or det_ref.rule_parameter,
        geography=payload.get("geography") or det_ref.geography,
        basis=payload.get("basis") or det_ref.basis,
        canonical_value=c_val,
        canonical_unit=c_unit,
        claims_unconditional_flat_rate=bool(
            payload.get("claims_unconditional_flat_rate", num_expr.claims_unconditional_flat_rate)
        ),
        is_corrupted_number=num_expr.is_corrupted,
        raw_question=question,
        raw_claim=candidate_claim,
        parser_name="llm_claim_parser_v1",
    )

    diag = LLMParseDiagnostics(
        schema_valid=True,
        parse_failed=(status == "failed_malformed"),
        unsupported_inference_detected=len(inferred_fields) > 0,
        unsupported_inferred_fields=inferred_fields,
    )
    return parsed, diag


class LLMClaimParser:
    """
    Optional LLM-based claim parser (Parser B).
    Requires explicit configuration via environment variables or LLMParserConfig,
    or an injected transport callable for offline testing.
    Never bypasses FieldGuard's deterministic verifier.
    """

    def __init__(
        self,
        config: LLMParserConfig | None = None,
        transport: Callable[[str, LLMParserConfig], dict[str, Any]] | None = None,
    ) -> None:
        self.config = config or LLMParserConfig.from_env()
        self.transport = transport
        self._cache: dict[str, dict[str, Any]] = {}
        if self.config.cache_path and self.config.cache_path.exists():
            try:
                self._cache = json.loads(self.config.cache_path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def is_available(self) -> tuple[bool, str]:
        if self.transport is not None:
            return True, "Custom transport adapter configured"
        if not self.config.is_configured():
            return (
                False,
                "SKIPPED: Optional LLM provider not configured (FIELDGUARD_LLM_PROVIDER / "
                "FIELDGUARD_LLM_MODEL / FIELDGUARD_LLM_API_KEY not set in environment).",
            )
        return True, f"Configured provider={self.config.provider}, model={self.config.model}"

    def _cache_key(self, question: str, candidate_claim: str) -> str:
        norm = f"{self.config.provider}|{self.config.model}|{self.config.prompt_version}|{self.config.schema_version}|{question.strip()}|{candidate_claim.strip()}"
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def _save_cache(self) -> None:
        if self.config.cache_path:
            self.config.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.config.cache_path.write_text(
                json.dumps(self._cache, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def _call_provider(self, prompt: str) -> dict[str, Any]:
        if self.transport is not None:
            return self.transport(prompt, self.config)

        if not self.config.is_configured():
            raise RuntimeError("LLMClaimParser is not configured with a provider/API key.")

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        last_err = ""
        for _ in range(max(1, self.config.max_retries)):
            try:
                resp = requests.post(
                    self.config.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout_sec,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    usage = data.get("usage", {})
                    return {
                        "content": content,
                        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                        "completion_tokens": int(usage.get("completion_tokens", 0)),
                    }
                last_err = f"HTTP {resp.status_code}"
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
        raise RuntimeError(f"LLM API call failed after retries: {last_err}")

    def parse_with_diagnostics(
        self,
        question: str,
        candidate_claim: str | None = None,
    ) -> tuple[ParsedClaim, LLMParseDiagnostics]:
        t0 = time.perf_counter()
        c_claim = candidate_claim or ""
        ckey = self._cache_key(question, c_claim)

        if ckey in self._cache:
            cached = self._cache[ckey]
            raw_text = cached.get("content", "")
            p_tok = int(cached.get("prompt_tokens", 0))
            c_tok = int(cached.get("completion_tokens", 0))
        else:
            prompt = build_llm_extraction_prompt(question, c_claim)
            try:
                resp = self._call_provider(prompt)
                raw_text = resp.get("content", "")
                p_tok = int(resp.get("prompt_tokens", 0))
                c_tok = int(resp.get("completion_tokens", 0))
                self._cache[ckey] = {
                    "content": raw_text,
                    "prompt_tokens": p_tok,
                    "completion_tokens": c_tok,
                }
                self._save_cache()
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000.0
                return (
                    ParsedClaim(
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
                        uncertain_fields=list(REQUIRED_PARSED_CLAIM_FIELDS),
                        raw_question=question,
                        raw_claim=c_claim,
                        parser_name="llm_claim_parser_error",
                    ),
                    LLMParseDiagnostics(
                        schema_valid=False,
                        parse_failed=True,
                        unsupported_inference_detected=False,
                        latency_ms=round(elapsed, 4),
                        error_message=str(exc),
                    ),
                )

        parsed, diag = validate_and_sanitize_llm_output(raw_text, question, c_claim)
        diag.latency_ms = round((time.perf_counter() - t0) * 1000.0, 4)
        diag.prompt_tokens = p_tok
        diag.completion_tokens = c_tok
        diag.estimated_cost_usd = round((p_tok * 0.00015 + c_tok * 0.0006) / 1000.0, 8)
        return parsed, diag

    def parse(self, question: str, candidate_claim: str | None = None) -> ParsedClaim:
        parsed, _ = self.parse_with_diagnostics(question, candidate_claim)
        return parsed
