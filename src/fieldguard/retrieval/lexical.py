"""Okapi BM25 lexical retrieval preserving numbers, percentages, crops, seasons, and qualifiers."""

from __future__ import annotations

import math
import re
from collections import Counter

from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.numeric_normalizer import extract_all_numeric_mentions
from fieldguard.retrieval.base import BaseRetriever, RetrievedEvidenceItem

STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "with", "by", "about", "as", "into",
    "of", "from", "that", "this", "it", "what", "which", "does", "do",
    "under", "can", "may", "will", "would", "should",
}


def tokenize_for_bm25(text: str, expand_domain_terms: bool = True) -> list[str]:
    """
    Tokenize text for BM25 while preserving exact numerical values, percentage notation,
    canonical numerical equivalents (e.g., '2%' <-> '2.0%'), ratios ('50:50', '90:10'),
    and qualification phrases ('whichever_is_less', 'sum_insured', 'actuarial_rate').
    """
    t = text.lower()
    tokens: list[str] = []

    # Preserve multi-word qualification and basis phrases as compound tokens
    compound_phrases = [
        ("whichever is less", "whichever_is_less"),
        ("sum insured", "sum_insured"),
        ("actuarial rate", "actuarial_rate"),
        ("actuarial premium rate", "actuarial_rate"),
        ("threshold yield", "threshold_yield"),
        ("post-harvest", "post_harvest"),
        ("post harvest", "post_harvest"),
        ("wild animal", "wild_animal"),
        ("north eastern", "north_eastern"),
        ("food grain", "food_grain"),
        ("food-grain", "food_grain"),
        ("food grains", "food_grain"),
        ("cut-and-spread", "cut_and_spread"),
        ("on-account", "on_account"),
        ("mid-season", "mid_season"),
        ("penal interest", "penal_interest"),
    ]
    for phrase, comp_tok in compound_phrases:
        if phrase in t:
            tokens.append(comp_tok)

    # Extract and canonicalize numerical mentions so '2%' matches '2.0% of Sum Insured'
    for m in extract_all_numeric_mentions(text):
        val_str = f"{m.canonical_value:g}"
        tokens.append(f"num_{val_str}_{m.canonical_unit}")
        tokens.append(f"num_{val_str}")

    # Standard alphanumeric + %/: tokens
    raw_words = re.findall(r"\d+(?:\.\d+)?%|\d+:\d+|[a-z0-9]+", t)
    for w in raw_words:
        if w in STOPWORDS:
            continue
        tokens.append(w)
        if w.endswith("%"):
            try:
                v = float(w[:-1])
                tokens.append(f"{v:g}%")
                tokens.append(f"{v:.1f}%")
            except ValueError:
                pass

    if expand_domain_terms:
        if any(c in raw_words for c in ("paddy", "wheat", "rice", "barley", "jowar", "bajra", "maize", "ragi", "gram", "lentil", "tur", "arhar", "moong", "urad", "mustard", "soybean", "groundnut", "sunflower", "sesame", "cereals", "millets", "pulses", "oilseeds", "oilseed")):
            tokens.extend(["food_grain", "food", "grain", "oilseed", "crops"])
        if any(c in raw_words for c in ("cotton", "sugarcane", "jute", "mesta", "potato", "onion", "banana", "chilli", "ginger", "turmeric", "tapioca", "horticultural", "commercial")):
            tokens.extend(["commercial", "horticultural", "annual", "crops"])
        if any(c in raw_words for c in ("assam", "meghalaya", "tripura", "manipur", "mizoram", "nagaland", "arunachal", "sikkim")):
            tokens.extend(["north_eastern", "ner", "states"])

    return tokens


class LexicalBM25Retriever(BaseRetriever):
    """Okapi BM25 retriever with numerical and domain-phrase preservation."""

    retriever_name = "lexical"

    def __init__(
        self,
        corpus_units: list[ExtractedEvidenceUnit],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        super().__init__(corpus_units)
        self.k1 = float(k1)
        self.b = float(b)

        self.doc_tokens: list[list[str]] = [
            tokenize_for_bm25(u.text, expand_domain_terms=True) for u in self.corpus_units
        ]
        self.doc_lens: list[int] = [len(toks) for toks in self.doc_tokens]
        self.avgdl: float = (
            sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 1.0
        )
        self.doc_freqs: dict[str, int] = {}
        self.term_Counters: list[Counter[str]] = []

        for toks in self.doc_tokens:
            cnt = Counter(toks)
            self.term_Counters.append(cnt)
            for term in cnt.keys():
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        self.num_docs = len(self.corpus_units)

    def _idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1.0 + (self.num_docs - df + 0.5) / (df + 0.5))

    def score_all(self, query: str) -> list[float]:
        if not self.corpus_units:
            return []
        q_tokens = tokenize_for_bm25(query, expand_domain_terms=True)
        scores = [0.0] * self.num_docs

        for idx, cnt in enumerate(self.term_Counters):
            dl = self.doc_lens[idx]
            norm_denom_part = self.k1 * (1.0 - self.b + self.b * (dl / max(self.avgdl, 1e-9)))
            doc_score = 0.0
            for qt in q_tokens:
                tf = cnt.get(qt, 0)
                if tf <= 0:
                    continue
                idf = self._idf(qt)
                doc_score += idf * ((tf * (self.k1 + 1.0)) / (tf + norm_denom_part))
            scores[idx] = doc_score
        return scores

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidenceItem]:
        if not self.corpus_units or top_k <= 0:
            return []

        scores = self.score_all(query)
        k = min(int(top_k), len(self.corpus_units))
        ranked_indices = sorted(
            range(len(self.corpus_units)),
            key=lambda i: (-scores[i], i),
        )[:k]

        results: list[RetrievedEvidenceItem] = []
        for rank_idx, doc_idx in enumerate(ranked_indices, start=1):
            unit = self.corpus_units[doc_idx]
            results.append(
                RetrievedEvidenceItem.from_unit(
                    unit=unit,
                    rank=rank_idx,
                    score=scores[doc_idx],
                    retriever_name=self.retriever_name,
                )
            )
        return results
