"""Local text embeddings for semantic search (plan increment 8, B04 and B08).

fastembed runs nomic-embed-text-v1.5-Q (quantised, 768 dimensions) on this
machine, so no ticket text or query leaves it. Nomic expects a task prefix:
documents and queries are embedded differently, so tools/embed.py and the API
both go through this module.
"""
import os
from pathlib import Path
import threading

MODEL = "nomic-ai/nomic-embed-text-v1.5-Q"
DIMENSIONS = 768
CACHE = Path(os.environ.get("FASTEMBED_CACHE_PATH") or Path.home() / ".cache" / "fastembed")


class Embedder:
    """Loads the model on first use, so the API starts without it and tests never load it."""

    def __init__(self):
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(MODEL, cache_dir=str(CACHE))
            return self._model

    def documents(self, texts, batch_size=64):
        return [vector.tolist() for vector in
                self._load().embed(["search_document: " + text for text in texts], batch_size=batch_size)]

    def query(self, text):
        return next(iter(self._load().embed(["search_query: " + text]))).tolist()


def as_vector(values):
    """pgvector text form, e.g. '[0.1,-0.2]'."""
    if len(values) != DIMENSIONS:
        raise ValueError(f"Expected {DIMENSIONS} dimensions, got {len(values)}")
    return "[" + ",".join(format(float(value), ".7g") for value in values) + "]"
