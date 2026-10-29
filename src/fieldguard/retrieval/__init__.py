"""FieldGuard retrieval package."""

from fieldguard.retrieval.base import BaseRetriever, RetrievedEvidenceItem
from fieldguard.retrieval.hybrid import HybridRetriever
from fieldguard.retrieval.lexical import LexicalBM25Retriever
from fieldguard.retrieval.semantic import SemanticRetriever
from fieldguard.retrieval.table_retrieval import TableAwareRetriever

__all__ = [
    "BaseRetriever",
    "RetrievedEvidenceItem",
    "SemanticRetriever",
    "LexicalBM25Retriever",
    "TableAwareRetriever",
    "HybridRetriever",
]
