"""Central registry and lookup mechanism for configured government schemes."""

from __future__ import annotations

from typing import Any

from fieldguard.schemes.base import BaseScheme
from fieldguard.schemes.pm_kisan import PMKisanScheme
from fieldguard.schemes.pmfby import PMFBYScheme
from fieldguard.schemes.mgnrega import MGNREGAScheme
from fieldguard.schemes.pmjay import PMJAYScheme
from fieldguard.schemes.pmay_g import PMAYGScheme
from fieldguard.schemes.pm_kusum import PMKusumScheme
from fieldguard.schemes.pmmy import PMMYScheme
from fieldguard.schemes.dynamic import GenericUploadedScheme


class SchemeRegistry:
    """Singleton-style registry for looking up scheme definitions by ID or alias."""

    _schemes: dict[str, BaseScheme] = {}
    _alias_map: dict[str, str] = {}

    @classmethod
    def register_scheme(cls, scheme: BaseScheme) -> None:
        """Register a scheme adapter with its primary key and all known aliases."""
        norm_id = scheme.scheme_id.upper()
        cls._schemes[norm_id] = scheme
        cls._alias_map[norm_id.lower()] = norm_id

        for alias in scheme.aliases:
            cls._alias_map[alias.lower().replace("-", "_")] = norm_id
            cls._alias_map[alias.lower().replace("_", "-")] = norm_id

    @classmethod
    def get_scheme(cls, scheme_name: str | None) -> BaseScheme | None:
        """Look up a scheme adapter case-insensitively using primary ID or alias."""
        if not scheme_name:
            return None

        # Initialize default schemes if empty
        if not cls._schemes:
            cls.initialize_default_schemes()

        clean_name = scheme_name.strip().lower()
        target_id = cls._alias_map.get(clean_name)
        if target_id and target_id in cls._schemes:
            return cls._schemes[target_id]

        # Direct upper-case lookup
        norm_key = clean_name.upper().replace("-", "_")
        return cls._schemes.get(norm_key)

    @classmethod
    def list_supported_schemes(cls) -> list[str]:
        """Return all supported primary scheme IDs."""
        if not cls._schemes:
            cls.initialize_default_schemes()
        return sorted(cls._schemes.keys())

    @classmethod
    def initialize_default_schemes(cls) -> None:
        """Register built-in government schemes and dynamic upload adapter."""
        cls.register_scheme(PMFBYScheme())
        cls.register_scheme(PMKisanScheme())
        cls.register_scheme(MGNREGAScheme())
        cls.register_scheme(PMJAYScheme())
        cls.register_scheme(PMAYGScheme())
        cls.register_scheme(PMKusumScheme())
        cls.register_scheme(PMMYScheme())
        cls.register_scheme(GenericUploadedScheme())


def get_scheme_adapter(scheme_name: str | None) -> BaseScheme | None:
    """Convenience helper to retrieve a scheme adapter by name or alias."""
    return SchemeRegistry.get_scheme(scheme_name)


def list_supported_schemes() -> list[str]:
    """Convenience helper to retrieve all registered scheme IDs."""
    return SchemeRegistry.list_supported_schemes()
