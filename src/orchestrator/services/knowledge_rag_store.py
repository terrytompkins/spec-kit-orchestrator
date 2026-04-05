"""SQLite + sqlite-vec RAG store with numpy cosine fallback when the extension is unavailable."""

from __future__ import annotations

import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

from orchestrator.services import knowledge_config as kcfg
from orchestrator.services.knowledge_paths import ensure_knowledge_dirs, rag_db_path


def _serialize_f32(vector: Sequence[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def _deserialize_f32(blob: bytes) -> np.ndarray:
    n = len(blob) // 4
    return np.frombuffer(blob, dtype=np.float32, count=n)


@dataclass
class RetrievedChunk:
    chunk_id: int
    doc_id: str
    chunk_index: int
    text: str
    distance: float


class KnowledgeRagStore:
    """
    Persists chunk text and embeddings. Uses sqlite-vec when loadable;
    otherwise stores float32 blobs and searches with cosine similarity in Python.
    """

    def __init__(self, project_path: Path):
        ensure_knowledge_dirs(project_path)
        self.db_path = rag_db_path(project_path)
        self._use_vec = False
        self._conn: Optional[sqlite3.Connection] = None

    def _connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._try_load_vec()
        self._init_schema()
        return self._conn

    def _try_load_vec(self) -> None:
        if self._conn is None:
            return
        try:
            import sqlite_vec  # type: ignore

            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            self._use_vec = True
        except Exception:
            self._use_vec = False

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_schema(self) -> None:
        conn = self._conn
        assert conn is not None
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        if self._use_vec:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks_meta (
                    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            dim = kcfg.EMBEDDING_DIMENSIONS
            conn.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0(embedding float[{dim}])"
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks_flat (
                    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )
        conn.commit()

    def _set_meta(self, key: str, value: str) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO rag_meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()

    def _get_meta(self, key: str) -> Optional[str]:
        conn = self._connect()
        row = conn.execute("SELECT value FROM rag_meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def validate_embedding_model(self) -> None:
        """Clear index if embedding model/dim changed."""
        conn = self._connect()
        stored = self._get_meta("embedding_model")
        current = f"{kcfg.EMBEDDING_MODEL}:{kcfg.EMBEDDING_DIMENSIONS}"
        if stored and stored != current:
            self.clear_all_vectors()
        self._set_meta("embedding_model", current)

    def clear_all_vectors(self) -> None:
        conn = self._connect()
        if self._use_vec:
            conn.execute("DELETE FROM chunk_vec")
            conn.execute("DELETE FROM chunks_meta")
        else:
            conn.execute("DELETE FROM chunks_flat")
        conn.commit()

    def delete_document_chunks(self, doc_id: str) -> None:
        conn = self._connect()
        if self._use_vec:
            rows = conn.execute(
                "SELECT chunk_id FROM chunks_meta WHERE doc_id = ?", (doc_id,)
            ).fetchall()
            for (cid,) in rows:
                conn.execute("DELETE FROM chunk_vec WHERE rowid = ?", (cid,))
            conn.execute("DELETE FROM chunks_meta WHERE doc_id = ?", (doc_id,))
        else:
            conn.execute("DELETE FROM chunks_flat WHERE doc_id = ?", (doc_id,))
        conn.commit()

    def insert_chunks(
        self,
        doc_id: str,
        chunk_texts: List[str],
        embeddings: List[List[float]],
    ) -> None:
        if len(chunk_texts) != len(embeddings):
            raise ValueError("chunk_texts and embeddings length mismatch")
        conn = self._connect()
        if self._use_vec:
            with conn:
                for idx, (text, emb) in enumerate(zip(chunk_texts, embeddings)):
                    conn.execute(
                        "INSERT INTO chunks_meta (doc_id, chunk_index, text) VALUES (?, ?, ?)",
                        (doc_id, idx, text),
                    )
                    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    conn.execute(
                        "INSERT INTO chunk_vec (rowid, embedding) VALUES (?, ?)",
                        (cid, _serialize_f32(emb)),
                    )
        else:
            with conn:
                for idx, (text, emb) in enumerate(zip(chunk_texts, embeddings)):
                    conn.execute(
                        """
                        INSERT INTO chunks_flat (doc_id, chunk_index, text, embedding)
                        VALUES (?, ?, ?, ?)
                        """,
                        (doc_id, idx, text, _serialize_f32(emb)),
                    )
        conn.commit()

    def search(
        self,
        query_embedding: List[float],
        doc_ids: Optional[Sequence[str]],
        top_k: int,
    ) -> List[RetrievedChunk]:
        conn = self._connect()
        doc_filter = set(doc_ids) if doc_ids else None
        q = np.array(query_embedding, dtype=np.float32)
        qn = np.linalg.norm(q)
        if qn > 0:
            q = q / qn

        if self._use_vec:
            # vec0 KNN: use `k = ?` (JOIN + LIMIT is unreliable per sqlite-vec docs)
            blob = _serialize_f32(query_embedding)
            knn = min(max(top_k * 6, top_k), 500)
            rows = conn.execute(
                "SELECT rowid, distance FROM chunk_vec WHERE embedding MATCH ? AND k = ?",
                (blob, knn),
            ).fetchall()
            out: List[RetrievedChunk] = []
            for rowid, dist in rows:
                m = conn.execute(
                    "SELECT doc_id, chunk_index, text FROM chunks_meta WHERE chunk_id = ?",
                    (rowid,),
                ).fetchone()
                if not m:
                    continue
                did, cidx, text = m[0], m[1], m[2]
                if doc_filter is not None and did not in doc_filter:
                    continue
                out.append(
                    RetrievedChunk(
                        chunk_id=int(rowid),
                        doc_id=str(did),
                        chunk_index=int(cidx),
                        text=str(text),
                        distance=float(dist),
                    )
                )
                if len(out) >= top_k:
                    break
            return out

        rows = conn.execute(
            "SELECT chunk_id, doc_id, chunk_index, text, embedding FROM chunks_flat"
        ).fetchall()
        scored: List[Tuple[float, RetrievedChunk]] = []
        for cid, did, cidx, text, emb_blob in rows:
            if doc_filter is not None and did not in doc_filter:
                continue
            v = _deserialize_f32(emb_blob).astype(np.float32)
            vn = np.linalg.norm(v)
            if vn > 0:
                v = v / vn
            sim = float(np.dot(q, v))
            dist = 1.0 - sim
            scored.append(
                (
                    dist,
                    RetrievedChunk(
                        chunk_id=int(cid),
                        doc_id=str(did),
                        chunk_index=int(cidx),
                        text=str(text),
                        distance=dist,
                    ),
                )
            )
        scored.sort(key=lambda x: x[0])
        return [r for _, r in scored[:top_k]]

    def uses_sqlite_vec(self) -> bool:
        self._connect()
        return self._use_vec

    def chunk_count(self) -> int:
        conn = self._connect()
        if self._use_vec:
            row = conn.execute("SELECT COUNT(*) FROM chunks_meta").fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM chunks_flat").fetchone()
        return int(row[0]) if row else 0


def store_backend_label(project_path: Path) -> str:
    s = KnowledgeRagStore(project_path)
    try:
        s._connect()
        return "sqlite-vec" if s._use_vec else "numpy-cosine (sqlite blobs)"
    finally:
        s.close()
