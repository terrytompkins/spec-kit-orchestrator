"""Recursive character splitting for RAG chunks."""

from __future__ import annotations

from typing import List


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if not text or chunk_size <= 0:
        return []
    overlap = max(0, min(overlap, chunk_size - 1)) if chunk_size > 1 else 0
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks if chunks else ([text.strip()] if text.strip() else [])
