"""Save uploads, extract text, chunk, embed, and index in rag.sqlite."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from openai import OpenAI

from orchestrator.services import knowledge_config as kcfg
from orchestrator.services.knowledge_chunking import chunk_text
from orchestrator.services.knowledge_extract import extract_text, is_supported_filename
from orchestrator.services.knowledge_embeddings import embed_texts
from orchestrator.services.knowledge_manifest import (
    DocumentRecord,
    classify_ingestion_mode,
    get_document,
    list_documents,
    new_doc_id,
    remove_document as manifest_remove,
    safe_original_filename,
    sha256_bytes,
    total_stored_bytes,
    upsert_document,
)
from orchestrator.services.knowledge_paths import doc_files_dir, ensure_knowledge_dirs, parsed_text_path
from orchestrator.services.knowledge_rag_store import KnowledgeRagStore


class KnowledgeIngestError(Exception):
    pass


def ingest_file(
    project_path: Path,
    file_bytes: bytes,
    original_filename: str,
    mime_type: str,
    client: OpenAI,
    doc_id: Optional[str] = None,
) -> DocumentRecord:
    """
    Write original bytes, parse, chunk, embed, index. Returns final DocumentRecord.
    """
    if not is_supported_filename(original_filename):
        raise KnowledgeIngestError("Unsupported file type.")
    if len(file_bytes) > kcfg.MAX_FILE_BYTES:
        raise KnowledgeIngestError(f"File exceeds maximum size ({kcfg.MAX_FILE_BYTES // (1024*1024)} MB).")

    ensure_knowledge_dirs(project_path)
    current_total = total_stored_bytes(project_path)
    if current_total + len(file_bytes) > kcfg.MAX_TOTAL_KNOWLEDGE_BYTES:
        raise KnowledgeIngestError("Total knowledge storage limit would be exceeded.")

    safe_name = safe_original_filename(original_filename)
    did = doc_id or new_doc_id()
    digest = sha256_bytes(file_bytes)
    doc_dir = doc_files_dir(project_path, did)
    doc_dir.mkdir(parents=True, exist_ok=True)
    stored_path = doc_dir / safe_name
    stored_path.write_bytes(file_bytes)
    relpath = f"files/{did}/{safe_name}"

    record = DocumentRecord(
        id=did,
        original_filename=original_filename,
        stored_relpath=relpath,
        mime_type=mime_type or "application/octet-stream",
        byte_size=len(file_bytes),
        sha256=digest,
        ingestion_status="pending",
        ingestion_mode="rag_only",
    )
    upsert_document(project_path, record)

    text, err = extract_text(file_bytes, original_filename)
    if err or not text:
        record.ingestion_status = "failed"
        record.error_message = err or "Empty document."
        upsert_document(project_path, record)
        raise KnowledgeIngestError(record.error_message or "Extraction failed.")

    parsed_text_path(project_path, did).parent.mkdir(parents=True, exist_ok=True)
    parsed_text_path(project_path, did).write_text(text, encoding="utf-8")

    mode = classify_ingestion_mode(len(text))
    record.ingestion_mode = mode
    record.ingestion_status = "parsed"
    record.chunking = {
        "strategy": "recursive_char",
        "chunk_size": kcfg.CHUNK_SIZE,
        "overlap": kcfg.CHUNK_OVERLAP,
    }
    upsert_document(project_path, record)

    chunks = chunk_text(text, kcfg.CHUNK_SIZE, kcfg.CHUNK_OVERLAP)
    if not chunks:
        record.ingestion_status = "failed"
        record.error_message = "No chunks produced."
        upsert_document(project_path, record)
        raise KnowledgeIngestError("No chunks produced from document.")

    store = KnowledgeRagStore(project_path)
    try:
        store.validate_embedding_model()
        store.delete_document_chunks(did)
        embeddings = embed_texts(client, chunks)
        if len(embeddings) != len(chunks):
            raise KnowledgeIngestError("Embedding count mismatch.")
        store.insert_chunks(did, chunks, embeddings)
    finally:
        store.close()

    record.ingestion_status = "indexed"
    record.error_message = None
    upsert_document(project_path, record)
    return record


def reindex_document(project_path: Path, doc_id: str, client: OpenAI) -> DocumentRecord:
    rec = get_document(project_path, doc_id)
    if rec is None:
        raise KnowledgeIngestError("Document not found.")
    path = doc_files_dir(project_path, doc_id) / Path(rec.stored_relpath).name
    if not path.exists():
        raise KnowledgeIngestError("Original file missing on disk.")
    data = path.read_bytes()

    manifest_remove(project_path, doc_id)
    return ingest_file(
        project_path,
        data,
        rec.original_filename,
        rec.mime_type,
        client,
        doc_id=doc_id,
    )


def delete_document_completely(project_path: Path, doc_id: str) -> bool:
    """Remove manifest entry, files, parsed text, and vector rows."""
    rec = get_document(project_path, doc_id)
    if rec is None:
        return False
    store = KnowledgeRagStore(project_path)
    try:
        store.delete_document_chunks(doc_id)
    finally:
        store.close()
    manifest_remove(project_path, doc_id)
    ddir = doc_files_dir(project_path, doc_id)
    if ddir.exists():
        shutil.rmtree(ddir, ignore_errors=True)
    pt = parsed_text_path(project_path, doc_id)
    if pt.exists():
        pt.unlink(missing_ok=True)
    return True


def reindex_all(project_path: Path, client: OpenAI) -> Tuple[int, List[str]]:
    """Re-parse and re-embed every manifest entry that still has files. Returns (ok_count, errors)."""
    errors: List[str] = []
    ok = 0
    for rec in list_documents(project_path):
        if rec.ingestion_status == "failed" and not (doc_files_dir(project_path, rec.id).exists()):
            continue
        try:
            reindex_document(project_path, rec.id, client)
            ok += 1
        except Exception as e:
            errors.append(f"{rec.original_filename}: {e}")
    return ok, errors
