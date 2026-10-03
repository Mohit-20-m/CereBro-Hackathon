"""Embedding helpers shared by the agents, with a tiny hashing fallback."""
from __future__ import annotations

import hashlib
import math

from ..ai.lexicon import tokens
from ..config import settings
from .engine import engine

HASH_MODEL = "hash-trigram-512"
_DIMS = 512


def hash_embed(text: str) -> list[float]:
    vec = [0.0] * _DIMS
    for tok in tokens(text):
        padded = f"#{tok}#"
        for g in [padded[i: i + 3] for i in range(max(1, len(padded) - 2))] + [f"w:{tok}"]:
            vec[int(hashlib.md5(g.encode()).hexdigest()[:8], 16) % _DIMS] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def current_embed_model() -> str:
    return settings.embed_model if engine.embed_ok else HASH_MODEL


def embed_texts(texts: list[str]) -> tuple[list[list[float]], str]:
    if not texts:
        return [], current_embed_model()
    if engine.embed_ok:
        try:
            return engine.embed(texts), settings.embed_model
        except Exception:  # noqa: BLE001
            pass
    return [hash_embed(t) for t in texts], HASH_MODEL


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def thresholds(model_name: str | None) -> dict[str, float]:
    """Similarity cut-offs for the multilingual MiniLM model vs the hash fallback."""
    if model_name == HASH_MODEL:
        return {"candidate": 0.30, "merge": 0.55, "topic_merge": 0.70, "strong": 0.6}
    return {"candidate": 0.35, "merge": 0.72, "topic_merge": 0.70, "strong": 0.62}
