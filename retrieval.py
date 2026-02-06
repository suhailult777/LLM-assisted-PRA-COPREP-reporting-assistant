"""
Retrieval engine for regulatory text chunks.

Two strategies:
  1. Gemini embeddings + cosine similarity  (primary)
  2. Keyword matching                       (fallback)

Embeddings are cached to a local .npy file so they are only generated once.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional

import numpy as np

from models import RegulatoryChunk

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CORPUS_PATH = pathlib.Path(__file__).parent / "data" / "regulatory_corpus.json"
_CACHE_DIR = pathlib.Path(__file__).parent / "data"
_EMBED_CACHE = _CACHE_DIR / "embeddings_cache.npy"
_IDS_CACHE = _CACHE_DIR / "embeddings_ids.json"

EMBED_MODEL = "gemini-embedding-001"


# ---------------------------------------------------------------------------
# Helper: cosine similarity
# ---------------------------------------------------------------------------

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between vector *a* and each row in matrix *b*."""
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norms = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return b_norms @ a_norm


# ---------------------------------------------------------------------------
# Retriever class
# ---------------------------------------------------------------------------

class SimpleRetriever:
    """Load regulatory corpus and retrieve relevant chunks."""

    def __init__(
        self,
        corpus_path: str | pathlib.Path = _CORPUS_PATH,
        gemini_client=None,
    ):
        self.corpus_path = pathlib.Path(corpus_path)
        self.chunks: list[RegulatoryChunk] = self._load_corpus()
        self._client = gemini_client  # google.genai.Client (optional)
        self._embeddings: Optional[np.ndarray] = None
        self._embed_ids: list[str] = []

    # ------------------------------------------------------------------
    # Load corpus
    # ------------------------------------------------------------------

    def _load_corpus(self) -> list[RegulatoryChunk]:
        with open(self.corpus_path, encoding="utf-8") as f:
            raw = json.load(f)
        return [RegulatoryChunk(**item) for item in raw]

    # ------------------------------------------------------------------
    # Embedding generation & caching
    # ------------------------------------------------------------------

    def _build_embeddings(self) -> bool:
        """Generate embeddings via Gemini and cache them. Returns True on success."""
        if self._client is None:
            return False
        try:
            texts = [c.text for c in self.chunks]
            ids = [c.chunk_id for c in self.chunks]

            vectors = []
            # Batch in groups of 5 to avoid rate limits
            batch_size = 5
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                for text in batch:
                    resp = self._client.models.embed_content(
                        model=EMBED_MODEL,
                        contents=text,
                    )
                    vectors.append(resp.embeddings[0].values)

            self._embeddings = np.array(vectors, dtype=np.float32)
            self._embed_ids = ids

            # Cache to disk
            np.save(str(_EMBED_CACHE), self._embeddings)
            with open(_IDS_CACHE, "w", encoding="utf-8") as f:
                json.dump(ids, f)

            return True
        except Exception as exc:
            print(f"[retrieval] Embedding generation failed: {exc}")
            return False

    def _load_cached_embeddings(self) -> bool:
        """Load cached embeddings from disk. Returns True on success."""
        if _EMBED_CACHE.exists() and _IDS_CACHE.exists():
            try:
                self._embeddings = np.load(str(_EMBED_CACHE))
                with open(_IDS_CACHE, encoding="utf-8") as f:
                    self._embed_ids = json.load(f)

                # Validate cache matches current corpus
                current_ids = [c.chunk_id for c in self.chunks]
                if self._embed_ids == current_ids:
                    return True
                else:
                    # Corpus changed – invalidate cache
                    self._embeddings = None
                    self._embed_ids = []
                    return False
            except Exception:
                return False
        return False

    def ensure_embeddings(self) -> bool:
        """Ensure embeddings are available (cached or freshly built)."""
        if self._embeddings is not None:
            return True
        if self._load_cached_embeddings():
            return True
        return self._build_embeddings()

    # ------------------------------------------------------------------
    # Retrieval: embedding-based (primary)
    # ------------------------------------------------------------------

    def retrieve_semantic(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve using Gemini embeddings + cosine similarity."""
        if not self.ensure_embeddings():
            return self.retrieve_keyword(query, top_k)

        try:
            resp = self._client.models.embed_content(
                model=EMBED_MODEL,
                contents=query,
            )
            q_vec = np.array(resp.embeddings[0].values, dtype=np.float32)
        except Exception:
            return self.retrieve_keyword(query, top_k)

        scores = _cosine_similarity(q_vec, self._embeddings)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "source": chunk.source,
                "section_ref": chunk.section_ref,
                "score": float(scores[idx]),
            })
        return results

    # ------------------------------------------------------------------
    # Retrieval: keyword-based (fallback)
    # ------------------------------------------------------------------

    def retrieve_keyword(self, query: str, top_k: int = 5) -> list[dict]:
        """Simple keyword scoring – always available, no API needed."""
        query_words = [w.lower() for w in query.split() if len(w) > 2]

        scored: list[tuple[float, int]] = []
        for i, chunk in enumerate(self.chunks):
            text_lower = chunk.text.lower()
            kw_lower = " ".join(chunk.keywords).lower()
            combined = text_lower + " " + kw_lower

            score = sum(1 for w in query_words if w in combined)
            # Boost exact field ID matches (e.g. "r0040")
            score += sum(3 for w in query_words if w.startswith("r0") and w in combined)
            scored.append((score, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        results = []
        for score, idx in top:
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "source": chunk.source,
                "section_ref": chunk.section_ref,
                "score": score,
            })
        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 5, method: str = "auto") -> list[dict]:
        """
        Retrieve top-k relevant chunks.

        method: "auto" (try semantic, fallback keyword), "semantic", "keyword"
        """
        if method == "keyword":
            return self.retrieve_keyword(query, top_k)
        if method == "semantic":
            return self.retrieve_semantic(query, top_k)

        # auto: try semantic first
        if self._client is not None:
            return self.retrieve_semantic(query, top_k)
        return self.retrieve_keyword(query, top_k)
