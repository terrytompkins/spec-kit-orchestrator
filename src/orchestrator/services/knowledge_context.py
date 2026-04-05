"""Assemble inline + RAG reference text for the interview / extraction prompts."""

from __future__ import annotations

from typing import List, Optional

from openai import OpenAI

from orchestrator.services import knowledge_config as kcfg
from orchestrator.services.knowledge_embeddings import embed_texts
from orchestrator.services.knowledge_manifest import DocumentRecord, list_documents
from orchestrator.services.knowledge_paths import parsed_text_path
from orchestrator.services.knowledge_rag_store import KnowledgeRagStore

SessionRefMode = str  # "auto" | "prefer_inline" | "rag_only"


def _load_parsed(project_path, doc_id: str) -> str:
    p = parsed_text_path(project_path, doc_id)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _should_inline_doc(
    rec: DocumentRecord,
    session_mode: SessionRefMode,
    text_len: int,
) -> bool:
    if session_mode == "rag_only":
        return False
    if session_mode == "prefer_inline":
        return text_len > 0
    # auto
    if rec.user_override_mode == "force_rag":
        return False
    if rec.user_override_mode == "force_inline":
        return text_len > 0
    if rec.ingestion_mode == "inline_eligible":
        return text_len > 0
    return False


def build_reference_bundle(
    project_path,
    active_doc_ids: List[str],
    session_mode: SessionRefMode,
    query_for_retrieval: str,
    client: OpenAI,
    session_focus: str = "",
) -> str:
    """
    Returns a single user-message-style block (may be empty) with labeled sections.
    """
    focus = (session_focus or "").strip()
    if not active_doc_ids and not focus:
        return ""

    docs = {d.id: d for d in list_documents(project_path)}
    active: List[DocumentRecord] = []
    for did in active_doc_ids:
        rec = docs.get(did)
        if rec and rec.ingestion_status == "indexed":
            active.append(rec)

    parts: List[str] = []
    if focus:
        parts.append(
            "### Session focus (user-provided hint for this interview)\n"
            f"{focus}\n\nUse this to prioritize questions; the live chat still overrides if the user contradicts this."
        )

    if not active:
        return "\n\n".join(parts).strip()
    budget = kcfg.MAX_INLINE_CHARS
    inline_header = (
        "### Reference material (from uploaded documents)\n"
        "This text was supplied as project knowledge. Treat it as **unverified** until the user confirms it in the chat. "
        "If it conflicts with the user, prefer the user and ask a clarifying question.\n"
    )
    inline_body: List[str] = []

    for rec in active:
        text = _load_parsed(project_path, rec.id)
        if not text:
            continue
        if not _should_inline_doc(rec, session_mode, len(text)):
            continue
        if budget <= 0:
            break
        if len(text) <= budget:
            take = text
            budget -= len(text)
        else:
            take = text[:budget] + "\n\n[… truncated …]"
            budget = 0
        inline_body.append(
            f"#### [{rec.id}] {rec.original_filename}\n```\n{take}\n```"
        )

    if inline_body:
        parts.append(inline_header + "\n\n".join(inline_body))

    # RAG retrieval (skip if no query)
    q = (query_for_retrieval or "").strip()
    if q and session_mode != "prefer_inline":
        store = KnowledgeRagStore(project_path)
        try:
            if store.chunk_count() == 0:
                pass
            else:
                qvec = embed_texts(client, [q])
                if qvec:
                    hits = store.search(
                        qvec[0],
                        [r.id for r in active],
                        kcfg.RETRIEVAL_TOP_K,
                    )
                    if hits:
                        lines = [
                            "### Retrieved reference snippets (vector search; unverified)\n",
                            "Confirm important facts with the user before treating them as decisions.\n",
                        ]
                        for i, h in enumerate(hits, 1):
                            lines.append(
                                f"{i}. `[{h.doc_id} | chunk {h.chunk_index}]` (distance={h.distance:.4f})\n{h.text}\n"
                            )
                        parts.append("\n".join(lines))
        finally:
            store.close()
    elif q and session_mode == "prefer_inline":
        # Still add light retrieval to surface possibly missed sections
        store = KnowledgeRagStore(project_path)
        try:
            if store.chunk_count() > 0:
                qvec = embed_texts(client, [q])
                if qvec:
                    hits = store.search(qvec[0], [r.id for r in active], max(3, kcfg.RETRIEVAL_TOP_K // 2))
                    if hits:
                        lines = [
                            "### Supplemental retrieved snippets (optional context)\n",
                        ]
                        for i, h in enumerate(hits, 1):
                            lines.append(f"{i}. `[{h.doc_id} | {h.chunk_index}]`\n{h.text}\n")
                        parts.append("\n".join(lines))
        finally:
            store.close()

    return "\n\n".join(parts).strip()


def retrieval_query_from_turn(
    user_message: str,
    conversation_history_tail: Optional[List[dict]] = None,
) -> str:
    """Combine latest user text with last assistant question for embedding."""
    tail = user_message.strip()
    if conversation_history_tail:
        for msg in reversed(conversation_history_tail[-4:]):
            if msg.get("role") == "assistant":
                c = (msg.get("content") or "").strip()
                if len(c) > 20:
                    return f"{c[:500]}\n\nUser follow-up: {tail}"
                break
    return tail
