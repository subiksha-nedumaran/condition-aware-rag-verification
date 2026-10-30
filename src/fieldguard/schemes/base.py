"""Base abstract class and context schemas for scheme-specific domain knowledge and condition adaptation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemeContextValidationResult:
    """Result of evaluating whether a parsed claim supplies all mandatory contextual dimensions."""

    is_valid: bool
    missing_fields: list[str] = field(default_factory=list)
    invalid_fields: list[str] = field(default_factory=list)
    details: str = ""


class BaseScheme(ABC):
    """
    Abstract interface for scheme-specific knowledge, condition taxonomy,
    parameter definitions, and contextual validation.
    """

    scheme_id: str
    full_name: str
    domain: str
    parameters: list[str]
    aliases: list[str] = []

    @abstractmethod
    def validate_claim_context(
        self,
        rule_parameter: str | None,
        context_dict: dict[str, Any],
        enable_switches: dict[str, bool] | None = None,
    ) -> SchemeContextValidationResult:
        """
        Validate whether all required contextual fields for the given parameter are present.
        """
        pass

    @abstractmethod
    def match_conditions(
        self,
        claimed_context: dict[str, Any],
        rule_context: dict[str, Any],
        rule_parameter: str,
        enable_switches: dict[str, bool] | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Evaluate whether rule conditions satisfy the claimed conditions.
        Returns (is_match, mismatch_reasons).
        """
        pass

    @abstractmethod
    def get_required_context_keys(self, rule_parameter: str) -> list[str]:
        """Return the list of mandatory contextual keys for a given rule parameter."""
        pass

