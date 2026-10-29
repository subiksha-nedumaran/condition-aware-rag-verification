"""Table-aware structured row retrieval preserving headers, cells, and version metadata."""

from __future__ import annotations

from fieldguard.claim_parser import DeterministicClaimParser
from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import extract_all_numeric_mentions
from fieldguard.retrieval.base import BaseRetriever, RetrievedEvidenceItem
from fieldguard.retrieval.lexical import LexicalBM25Retriever


class TableAwareRetriever(BaseRetriever):
    """
    Retriever specialized for structured policy table rows (`evidence_type == 'table_row'`),
    scoring header-cell alignment, season/crop-category match, version match, and numerical match,
    backed by BM25 lexical scoring over the full corpus.
    """

    retriever_name = "table"

    def __init__(
        self,
        corpus_units: list[ExtractedEvidenceUnit],
        exact_numeric_boost: float = 2.5,
        table_row_boost: float = 3.0,
        header_context_boost: float = 2.5,
    ) -> None:
        super().__init__(corpus_units)
        self.bm25 = LexicalBM25Retriever(corpus_units)
        self.parser = DeterministicClaimParser()
        self.exact_numeric_boost = exact_numeric_boost
        self.table_row_boost = table_row_boost
        self.header_context_boost = header_context_boost

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidenceItem]:
        if not self.corpus_units or top_k <= 0:
            return []

        base_scores = self.bm25.score_all(query)
        parsed = self.parser.parse(query)
        q_mentions = extract_all_numeric_mentions(query)
        q_vals = {round(m.canonical_value, 4) for m in q_mentions}

        total_scores: list[float] = []
        for idx, unit in enumerate(self.corpus_units):
            score = base_scores[idx]
            utext_low = unit.text.lower()

            if unit.evidence_type == "table_row" and unit.headers:
                score += self.table_row_boost

                # Boost when season and crop category match inside the structured row cells
                if parsed.season and parsed.season in utext_low:
                    score += self.header_context_boost
                if parsed.crop_category == "food_grain_and_oilseed" and (
                    "food grain" in utext_low or "oilseed" in utext_low
                ):
                    score += self.header_context_boost
                elif parsed.crop_category == "commercial_and_horticultural" and (
                    "commercial" in utext_low or "horticultural" in utext_low
                ):
                    score += self.header_context_boost
                elif parsed.crop_category == "unirrigated_crops" and "unirrigated" in utext_low:
                    score += self.header_context_boost
                elif parsed.crop_category == "irrigated_crops" and "irrigated" in utext_low and "unirrigated" not in utext_low:
                    score += self.header_context_boost
                elif parsed.crop_category == "perennial_betelvine_pilot" and "betelvine" in utext_low:
                    score += self.header_context_boost

                if parsed.geography == "north_eastern_states" and "north eastern" in utext_low:
                    score += self.header_context_boost
                elif parsed.geography == "general_states" and "general states" in utext_low:
                    score += self.header_context_boost

            # Policy era alignment
            if parsed.requested_policy_version == "2016_historical" and unit.policy_era == "historical_2016":
                score += 3.0
            elif parsed.requested_policy_version in ("2023_guidelines", None) and unit.policy_era == "guidelines_2023":
                score += 1.5

            # Exact numerical match boost
            if q_vals:
                u_mentions = extract_all_numeric_mentions(unit.text)
                for um in u_mentions:
                    if round(um.canonical_value, 4) in q_vals:
                        score += self.exact_numeric_boost
                        break

            total_scores.append(score)

        k = min(int(top_k), len(self.corpus_units))
        ranked_indices = sorted(
            range(len(self.corpus_units)),
            key=lambda i: (-total_scores[i], i),
        )[:k]

        results: list[RetrievedEvidenceItem] = []
        for rank_idx, doc_idx in enumerate(ranked_indices, start=1):
            unit = self.corpus_units[doc_idx]
            results.append(
                RetrievedEvidenceItem.from_unit(
                    unit=unit,
                    rank=rank_idx,
                    score=total_scores[doc_idx],
                    retriever_name=self.retriever_name,
                )
            )
        return results
