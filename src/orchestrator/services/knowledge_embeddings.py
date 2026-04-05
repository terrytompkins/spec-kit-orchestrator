"""OpenAI text embeddings for knowledge RAG."""

from __future__ import annotations

from typing import List, Optional

from openai import OpenAI

from orchestrator.services import knowledge_config as kcfg


def embed_texts(client: OpenAI, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    """Returns one embedding vector per input string (same order)."""
    if not texts:
        return []
    model = model or kcfg.EMBEDDING_MODEL
    # Batch in groups to respect payload size
    batch_size = 64
    all_vecs: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client.embeddings.create(model=model, input=batch, dimensions=kcfg.EMBEDDING_DIMENSIONS)
        # API returns data in arbitrary order — sort by index
        ordered = sorted(resp.data, key=lambda d: d.index)
        for item in ordered:
            all_vecs.append(list(item.embedding))
    return all_vecs
