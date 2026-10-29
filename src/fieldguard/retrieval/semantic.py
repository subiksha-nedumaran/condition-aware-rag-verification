"""Semantic retrieval using sentence-transformers/all-MiniLM-L6-v2 on CPU with embedding caching."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from fieldguard.metadata import ExtractedEvidenceUnit
from fieldguard.retrieval.base import BaseRetriever, RetrievedEvidenceItem


def _layer_norm(x: np.ndarray, weight: np.ndarray, bias: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    mean = np.mean(x, axis=-1, keepdims=True)
    var = np.var(x, axis=-1, keepdims=True)
    inv_std = (1.0 / np.sqrt(var + np.float32(eps))).astype(np.float32)
    return (x - mean) * inv_std * weight + bias


def _gelu(x: np.ndarray) -> np.ndarray:
    c = np.float32(np.sqrt(2.0 / np.pi))
    k = np.float32(0.044715)
    return np.float32(0.5) * x * (np.float32(1.0) + np.tanh(c * (x + k * x * x * x)))


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    x_max = np.max(x, axis=axis, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=axis, keepdims=True)


class MiniLML6V2SafetensorsEncoder:
    """
    Exact CPU inference engine for `sentence-transformers/all-MiniLM-L6-v2`
    using HuggingFace Rust tokenizers and safetensors weights.
    """

    def __init__(
        self,
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_length: int = 256,
        batch_size: int = 64,
    ) -> None:
        from huggingface_hub import snapshot_download
        from safetensors.numpy import load_file
        from tokenizers import Tokenizer

        self.model_id = model_id
        self.max_length = max_length
        self.batch_size = batch_size

        resolved_dir = snapshot_download(repo_id=model_id, local_files_only=True)
        model_dir = Path(resolved_dir)

        with (model_dir / "config.json").open("r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.weights = load_file(str(model_dir / "model.safetensors"))
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        pad_id = int(self.config.get("pad_token_id", 0))
        self.tokenizer.enable_padding(pad_id=pad_id, pad_token="[PAD]")
        self.tokenizer.enable_truncation(max_length=self.max_length)

        self.num_layers = int(self.config.get("num_hidden_layers", 6))
        self.num_heads = int(self.config.get("num_attention_heads", 12))
        self.hidden_size = int(self.config.get("hidden_size", 384))
        self.head_dim = self.hidden_size // self.num_heads
        self.ln_eps = float(self.config.get("layer_norm_eps", 1e-12))

    def _p(self, key: str) -> np.ndarray:
        if key in self.weights:
            return self.weights[key]
        prefixed = f"bert.{key}"
        if prefixed in self.weights:
            return self.weights[prefixed]
        raise KeyError(f"Weight tensor '{key}' not found in {self.model_id}.")

    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.hidden_size), dtype=np.float32)

        all_embeddings: list[np.ndarray] = []
        w_word = self._p("embeddings.word_embeddings.weight")
        w_pos = self._p("embeddings.position_embeddings.weight")
        w_tok = self._p("embeddings.token_type_embeddings.weight")
        emb_ln_w = self._p("embeddings.LayerNorm.weight")
        emb_ln_b = self._p("embeddings.LayerNorm.bias")

        for start in range(0, len(texts), self.batch_size):
            batch_texts = [t if t.strip() else "[PAD]" for t in texts[start : start + self.batch_size]]
            encoded = self.tokenizer.encode_batch(batch_texts)
            input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
            attn_mask = np.array([e.attention_mask for e in encoded], dtype=np.float32)

            bsz, seq_len = input_ids.shape
            pos_ids = np.arange(seq_len, dtype=np.int64)[None, :]

            hidden = w_word[input_ids] + w_pos[pos_ids] + w_tok[0]
            hidden = _layer_norm(hidden, emb_ln_w, emb_ln_b, self.ln_eps)

            ext_mask = ((np.float32(1.0) - attn_mask[:, None, None, :]) * np.float32(-10000.0)).astype(np.float32)
            scale_factor = np.float32(1.0 / np.sqrt(float(self.head_dim)))

            for layer_idx in range(self.num_layers):
                prefix = f"encoder.layer.{layer_idx}"
                q_w = self._p(f"{prefix}.attention.self.query.weight")
                q_b = self._p(f"{prefix}.attention.self.query.bias")
                k_w = self._p(f"{prefix}.attention.self.key.weight")
                k_b = self._p(f"{prefix}.attention.self.key.bias")
                v_w = self._p(f"{prefix}.attention.self.value.weight")
                v_b = self._p(f"{prefix}.attention.self.value.bias")

                q = (hidden @ q_w.T + q_b).reshape(bsz, seq_len, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
                k = (hidden @ k_w.T + k_b).reshape(bsz, seq_len, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
                v = (hidden @ v_w.T + v_b).reshape(bsz, seq_len, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)

                scores = (q @ k.transpose(0, 1, 3, 2)) * scale_factor
                scores = scores + ext_mask
                probs = _softmax(scores, axis=-1)

                context = (probs @ v).transpose(0, 2, 1, 3).reshape(bsz, seq_len, self.hidden_size)
                ao_w = self._p(f"{prefix}.attention.output.dense.weight")
                ao_b = self._p(f"{prefix}.attention.output.dense.bias")
                ao_ln_w = self._p(f"{prefix}.attention.output.LayerNorm.weight")
                ao_ln_b = self._p(f"{prefix}.attention.output.LayerNorm.bias")

                attn_out = context @ ao_w.T + ao_b
                hidden = _layer_norm(hidden + attn_out, ao_ln_w, ao_ln_b, self.ln_eps)

                int_w = self._p(f"{prefix}.intermediate.dense.weight")
                int_b = self._p(f"{prefix}.intermediate.dense.bias")
                out_w = self._p(f"{prefix}.output.dense.weight")
                out_b = self._p(f"{prefix}.output.dense.bias")
                out_ln_w = self._p(f"{prefix}.output.LayerNorm.weight")
                out_ln_b = self._p(f"{prefix}.output.LayerNorm.bias")

                inter = _gelu(hidden @ int_w.T + int_b)
                layer_out = inter @ out_w.T + out_b
                hidden = _layer_norm(hidden + layer_out, out_ln_w, out_ln_b, self.ln_eps)

            mask_expanded = attn_mask[:, :, None]
            sum_embeddings = np.sum(hidden * mask_expanded, axis=1)
            sum_mask = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
            pooled = (sum_embeddings / sum_mask).astype(np.float32)

            if normalize:
                norms = np.linalg.norm(pooled, axis=1, keepdims=True)
                pooled = pooled / np.clip(norms, a_min=1e-12, a_max=None)

            all_embeddings.append(pooled)

        return np.vstack(all_embeddings)


_SHARED_MINILM_ENCODER: MiniLML6V2SafetensorsEncoder | None = None


def get_shared_minilm_encoder(
    model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
    max_length: int = 256,
) -> MiniLML6V2SafetensorsEncoder:
    global _SHARED_MINILM_ENCODER
    if _SHARED_MINILM_ENCODER is None or _SHARED_MINILM_ENCODER.model_id != model_id:
        _SHARED_MINILM_ENCODER = MiniLML6V2SafetensorsEncoder(
            model_id=model_id,
            max_length=max_length,
        )
    return _SHARED_MINILM_ENCODER


class SemanticRetriever(BaseRetriever):
    """
    Dense semantic retriever using `sentence-transformers/all-MiniLM-L6-v2`
    and exact inner-product vector indexing (equivalent to FAISS IndexFlatIP on L2-normalized vectors).
    """

    retriever_name = "semantic"

    def __init__(
        self,
        corpus_units: list[ExtractedEvidenceUnit],
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_version: str = "minilm_l6_v2_exact_ip_v1",
        max_length: int = 256,
        cache_path: Path | None = None,
    ) -> None:
        super().__init__(corpus_units)
        self.model_id = model_id
        self.index_version = index_version
        self.max_length = max_length
        self.encoder = get_shared_minilm_encoder(model_id=model_id, max_length=max_length)
        self._query_cache: dict[str, np.ndarray] = {}

        if cache_path is None:
            project_root = Path(__file__).resolve().parents[3]
            cache_path = project_root / "cache" / "embeddings" / "minilm_l6_v2_corpus_cache.npz"
        self.cache_path = cache_path
        self.corpus_embeddings = self._load_or_compute_corpus_embeddings()

    def _compute_corpus_fingerprint(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(f"{self.model_id}|{self.index_version}|{self.max_length}".encode("utf-8"))
        for u in self.corpus_units:
            hasher.update(f"{u.evidence_id}:{u.text}".encode("utf-8"))
        return hasher.hexdigest()

    def _load_or_compute_corpus_embeddings(self) -> np.ndarray:
        if not self.corpus_units:
            return np.zeros((0, self.encoder.hidden_size), dtype=np.float32)

        fp = self._compute_corpus_fingerprint()
        if self.cache_path.exists():
            try:
                data = np.load(str(self.cache_path), allow_pickle=False)
                if str(data["fingerprint"]) == fp:
                    return data["embeddings"].astype(np.float32)
            except Exception:
                pass

        texts = [u.text for u in self.corpus_units]
        embs = self.encoder.encode(texts, normalize=True)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(self.cache_path),
            embeddings=embs,
            fingerprint=np.array(fp),
            model_id=np.array(self.model_id),
            index_version=np.array(self.index_version),
        )
        return embs

    def get_index_metadata(self) -> dict[str, Any]:
        return {
            "retriever_name": self.retriever_name,
            "model_id": self.model_id,
            "index_version": self.index_version,
            "max_length": self.max_length,
            "corpus_size": len(self.corpus_units),
            "embedding_dim": int(self.corpus_embeddings.shape[1]) if self.corpus_embeddings.size else 384,
        }

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidenceItem]:
        if not self.corpus_units or top_k <= 0:
            return []

        q_clean = query.strip()
        if q_clean not in self._query_cache:
            self._query_cache[q_clean] = self.encoder.encode([q_clean], normalize=True)[0]
        q_vec = self._query_cache[q_clean]

        scores = (self.corpus_embeddings @ q_vec).astype(np.float64)
        k = min(int(top_k), len(self.corpus_units))
        ranked_indices = np.argsort(-scores)[:k]

        results: list[RetrievedEvidenceItem] = []
        for rank_idx, doc_idx in enumerate(ranked_indices, start=1):
            unit = self.corpus_units[int(doc_idx)]
            results.append(
                RetrievedEvidenceItem.from_unit(
                    unit=unit,
                    rank=rank_idx,
                    score=float(scores[int(doc_idx)]),
                    retriever_name=self.retriever_name,
                )
            )
        return results
