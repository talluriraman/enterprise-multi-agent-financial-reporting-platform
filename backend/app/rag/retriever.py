"""
RAG over internal JSON knowledge for 2026 financial context.

If Azure OpenAI embeddings are configured, uses cosine similarity; otherwise keyword overlap.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

from app.config import settings

_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample_expenses_2026.json"


def _load_data() -> dict[str, Any]:
    if not _DATA_PATH.exists():
        return {"year": 2026, "monthly": [], "rag_chunks": []}
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def _simple_embed(text: str, dim: int = 64) -> np.ndarray:
    """Deterministic pseudo-embedding for offline POC."""
    v = np.zeros(dim, dtype=np.float32)
    for i, ch in enumerate(text.lower()):
        v[i % dim] += ord(ch) / 1000.0
    n = np.linalg.norm(v) or 1.0
    return v / n


async def embed_texts(texts: list[str]) -> list[list[float]]:
    # Optional: Azure OpenAI embeddings
    endpoint = settings.azure_openai_endpoint
    key = settings.azure_openai_api_key
    if endpoint and (key or settings.use_managed_identity):
        try:
            from openai import AsyncAzureOpenAI
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            if settings.use_managed_identity and not key:
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
                client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=settings.azure_openai_api_version,
                )
            else:
                client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=key,
                    api_version=settings.azure_openai_api_version,
                )
            dep = settings.azure_embedding_deployment
            resp = await client.embeddings.create(model=dep, input=texts)
            return [d.embedding for d in resp.data]
        except Exception:
            pass
    return [_simple_embed(t).tolist() for t in texts]


def _cosine(a: list[float], b: list[float]) -> float:
    aa = np.array(a, dtype=np.float32)
    bb = np.array(b, dtype=np.float32)
    denom = (np.linalg.norm(aa) * np.linalg.norm(bb)) or 1.0
    return float(np.dot(aa, bb) / denom)


async def retrieve_context(query: str, top_k: int = 4) -> str:
    data = _load_data()
    chunks: list[str] = list(data.get("rag_chunks", []))
    # Add structured snippet from monthly data when query mentions expenses/monthly/2026
    if re.search(r"2026|monthly|expense", query, re.I):
        monthly = data.get("monthly", [])
        chunks.append(
            "Structured 2026 monthly totals (USD): "
            + ", ".join(f"M{m['month']}={m['total_expenses']}" for m in monthly)
        )

    if not chunks:
        return ""

    q_emb = (await embed_texts([query]))[0]
    chunk_embs = await embed_texts(chunks)
    scored = sorted(
        range(len(chunks)),
        key=lambda i: _cosine(q_emb, chunk_embs[i]),
        reverse=True,
    )[:top_k]
    return "\n".join(chunks[i] for i in scored)
