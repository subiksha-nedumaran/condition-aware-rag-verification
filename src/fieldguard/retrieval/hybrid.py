"""Hybrid retrieval combining lexical BM25, dense semantic embeddings, and table-aware rankings via RRF."""

from __future__ import annotations

from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.retrieval.base import BaseRetriever, RetrievedEvidenceItem
from fieldguard.retrieval.lexical import LexicalBM25Retriever
from fieldguard.retrieval.semantic import SemanticRetriever
from fieldguard.retrieval.table_retrieval import TableAwareRetriever


class HybridRetriever(BaseRetriever):
    """
    Weighted Reciprocal Rank Fusion (RRF) retriever combining dense semantic
    (`sentence-transformers/all-MiniLM-L6-v2`), lexical BM25, and table-aware rankings.
    Preserves all provenance metadata when merging rankings.
    """

    retriever_name = "hybrid"

    def __init__(
        self,
        corpus_units: list[ExtractedEvidenceUnit],
        semantic_retriever: SemanticRetriever | None = None,
        lexical_retriever: LexicalBM25Retriever | None = None,
        table_retriever: TableAwareRetriever | None = None,
        rrf_k: int = 60,
        semantic_weight: float = 0.35,
        lexical_weight: float = 0.40,
        table_weight: float = 0.25,
    ) -> None:
        super().__init__(corpus_units)
        self.semantic = semantic_retriever or SemanticRetriever(corpus_units)
        self.lexical = lexical_retriever or LexicalBM25Retriever(corpus_units)
        self.table = table_retriever or TableAwareRetriever(corpus_units)
        self.rrf_k = int(rrf_k)
        self.semantic_weight = float(semantic_weight)
        self.lexical_weight = float(lexical_weight)
        self.table_weight = float(table_weight)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidenceItem]:
        if not self.corpus_units or top_k <= 0:
            return []

        n_all = len(self.corpus_units)
        sem_items = self.semantic.retrieve(query, top_k=n_all)
        lex_items = self.lexical.retrieve(query, top_k=n_all)
        tbl_items = self.table.retrieve(query, top_k=n_all)

        rrf_scores: dict[str, float] = {u.evidence_id: 0.0 for u in self.corpus_units}

        for item in sem_items:
            rrf_scores[item.evidence_id] += self.semantic_weight / (self.rrf_k + item.rank)
        for item in lex_items:
            rrf_scores[item.evidence_id] += self.lexical_weight / (self.rrf_k + item.rank)
        for item in tbl_items:
            rrf_scores[item.evidence_id] += self.table_weight / (self.rrf_k + item.rank)

        k = min(int(top_k), n_all)
        ranked_ev_ids = sorted(
            rrf_scores.keys(),
            key=lambda eid: (-rrf_scores[eid], eid),
        )[:k]

        results: list[RetrievedEvidenceItem] = []
        for rank_idx, eid in enumerate(ranked_ev_ids, start=1):
            unit = self.unit_by_id[eid]
            results.append(
                RetrievedEvidenceItem.from_unit(
                    unit=unit,
                    rank=rank_idx,
                    score=rrf_scores[eid],
                    retriever_name=self.retriever_name,
                )
            )
        return results
