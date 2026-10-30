"""Modular scheme adapters and registry for multi-scheme condition matching."""

from __future__ import annotations

from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult
from fieldguard.schemes.pm_kisan import PMKisanScheme
from fieldguard.schemes.pmfby import PMFBYScheme
from fieldguard.schemes.registry import SchemeRegistry, get_scheme_adapter

__all__ = [
    "BaseScheme",
    "SchemeContextValidationResult",
    "PMFBYScheme",
    "PMKisanScheme",
    "SchemeRegistry",
    "get_scheme_adapter",
]

