"""Keep only the active upload backend in the current user's session."""

import hashlib
from typing import Any, MutableMapping

from fieldguard.uploaded_doc_engine import process_uploaded_document
from fieldguard.verifier import FieldGuardVerifier


def load_uploaded_backend(state: MutableMapping[str, Any], file_bytes: bytes, file_name: str):
    key = ("numeric-v2", file_name, hashlib.sha256(file_bytes).hexdigest())
    cached = state.get("fieldguard_upload_backend")
    if cached is not None and cached[0] == key:
        return cached[1]
    # Drop stale data even if the replacement file fails ingestion.
    state.pop("fieldguard_upload_backend", None)
    from fieldguard.evaluation.runner import build_all_retrievers

    store, units, rules = process_uploaded_document(file_bytes, file_name)
    backend = (store, units, rules, build_all_retrievers(store), FieldGuardVerifier(store))
    state["fieldguard_upload_backend"] = (key, backend)
    return backend
