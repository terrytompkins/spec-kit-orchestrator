"""Unit tests for project knowledge services."""

import json
from pathlib import Path

import pytest

from orchestrator.services.knowledge_chunking import chunk_text
from orchestrator.services.knowledge_manifest import (
    DocumentRecord,
    classify_ingestion_mode,
    load_manifest,
    remove_document,
    upsert_document,
)
from orchestrator.services.knowledge_paths import ensure_knowledge_dirs
from orchestrator.services.knowledge_rag_store import KnowledgeRagStore
from orchestrator.services import interview_state as interview_state_service
from orchestrator.services import knowledge_config as kcfg


def test_chunk_text_splits_and_overlaps():
    text = "a" * 100
    chunks = chunk_text(text, chunk_size=30, overlap=5)
    assert len(chunks) >= 3
    joined = "".join(chunks)
    assert "a" * 100 in joined or joined.replace("\n", "") == "a" * 100


def test_classify_ingestion_mode():
    assert classify_ingestion_mode(100) == "inline_eligible"
    assert classify_ingestion_mode(kcfg.INLINE_CHAR_THRESHOLD) == "inline_eligible"
    assert classify_ingestion_mode(kcfg.INLINE_CHAR_THRESHOLD + 1) == "rag_only"


def test_manifest_roundtrip(tmp_path: Path):
    ensure_knowledge_dirs(tmp_path)
    rec = DocumentRecord(
        id="doc-1",
        original_filename="n.txt",
        stored_relpath="files/doc-1/n.txt",
        mime_type="text/plain",
        byte_size=4,
        sha256="ab" * 32,
        ingestion_status="indexed",
        ingestion_mode="inline_eligible",
    )
    upsert_document(tmp_path, rec)
    loaded = load_manifest(tmp_path)
    assert len(loaded["documents"]) == 1
    assert loaded["documents"][0]["id"] == "doc-1"
    remove_document(tmp_path, "doc-1")
    assert load_manifest(tmp_path)["documents"] == []


def test_rag_store_numpy_fallback(tmp_path: Path, monkeypatch):
    import sys

    fake = type(sys)("sqlite_vec")

    def load_fail(_db):
        raise RuntimeError("no extension")

    fake.load = load_fail
    monkeypatch.setitem(sys.modules, "sqlite_vec", fake)

    (tmp_path / ".specify" / "orchestrator").mkdir(parents=True)
    ensure_knowledge_dirs(tmp_path)
    store = KnowledgeRagStore(tmp_path)
    store._connect()
    assert store._use_vec is False
    store.validate_embedding_model()
    emb = [[0.0] * kcfg.EMBEDDING_DIMENSIONS, [1.0] * kcfg.EMBEDDING_DIMENSIONS]
    emb[0][0] = 1.0
    store.insert_chunks("d1", ["alpha", "beta"], emb)
    q = [1.0] + [0.0] * (kcfg.EMBEDDING_DIMENSIONS - 1)
    hits = store.search(q, ["d1"], top_k=1)
    assert len(hits) == 1
    assert "alpha" in hits[0].text
    store.close()


def test_interview_state_preserves_knowledge(tmp_path: Path):
    (tmp_path / ".specify" / "orchestrator").mkdir(parents=True)
    interview_state_service.save(
        tmp_path,
        [{"role": "user", "content": "hi"}],
        False,
        None,
        active_document_ids=["a", "b"],
        session_focus="checkout",
        knowledge_reference_mode="rag_only",
    )
    state = interview_state_service.load(tmp_path)
    assert state["active_document_ids"] == ["a", "b"]
    assert state["session_focus"] == "checkout"
    assert state["knowledge_reference_mode"] == "rag_only"


def test_interview_state_v1_load(tmp_path: Path):
    (tmp_path / ".specify" / "orchestrator").mkdir(parents=True)
    p = tmp_path / ".specify" / "orchestrator" / "interview_state.json"
    p.write_text(
        json.dumps(
            {
                "version": 1,
                "chat_messages": [{"role": "assistant", "content": "x"}],
                "interview_complete": False,
                "generated_parameters": None,
                "saved_at": "2020-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    state = interview_state_service.load(tmp_path)
    assert state is not None
    assert state["version"] == 1
    assert state["active_document_ids"] == []
    assert state["knowledge_reference_mode"] == "auto"
