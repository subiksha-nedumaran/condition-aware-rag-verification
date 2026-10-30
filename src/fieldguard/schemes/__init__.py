"""Modular scheme adapters and registry for multi-scheme condition matching."""

from __future__ import annotations

from fieldguard.schemes.base import BaseScheme, SchemeContextValidationResult
from fieldguard.schemes.pm_kisan import PMKisanScheme
from fieldguard.schemes.pmfby import PMFBYScheme
from fieldguard.schemes.mgnrega import MGNREGAScheme
from fieldguard.schemes.pmjay import PMJAYScheme
from fieldguard.schemes.pmay_g import PMAYGScheme
from fieldguard.schemes.pm_kusum import PMKusumScheme
from fieldguard.schemes.pmmy import PMMYScheme
from fieldguard.schemes.dynamic import GenericUploadedScheme
from fieldguard.schemes.registry import SchemeRegistry, get_scheme_adapter, list_supported_schemes

__all__ = [
    "BaseScheme",
    "SchemeContextValidationResult",
    "PMFBYScheme",
    "PMKisanScheme",
    "MGNREGAScheme",
    "PMJAYScheme",
    "PMAYGScheme",
    "PMKusumScheme",
    "PMMYScheme",
    "GenericUploadedScheme",
    "SchemeRegistry",
    "get_scheme_adapter",
    "list_supported_schemes",
]
