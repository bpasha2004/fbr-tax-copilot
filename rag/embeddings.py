"""Embedding provider with a real Ollama path and deterministic local fallback.

The local provider is intentionally lightweight and reproducible for CI/smoke tests.
Production RAG should use Ollama embeddings for semantic quality.
"""
import hashlib
import math
import re
import httpx
from config.settings import settings


def _local_embedding(text: str) -> list[float]:
    """Deterministic hashed bag-of-words embedding; no network/model required."""
    dim = settings.LOCAL_EMBEDDING_DIM
    vec = [0.0] * dim
    tokens = re.findall(r"[a-zA-Z0-9_]{2,}", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


async def embed_text(text: str) -> list[float]:
    if settings.EMBEDDING_PROVIDER == "local":
        return _local_embedding(text)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


def embed_text_sync(text: str) -> list[float]:
    if settings.EMBEDDING_PROVIDER == "local":
        return _local_embedding(text)
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]
