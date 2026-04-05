"""Manage project knowledge uploads, manifest, and RAG index."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from orchestrator.services.knowledge_ingest import (
    KnowledgeIngestError,
    delete_document_completely,
    ingest_file,
    reindex_all,
    reindex_document,
)
from orchestrator.services.knowledge_manifest import list_documents, upsert_document
from orchestrator.services.knowledge_rag_store import KnowledgeRagStore, store_backend_label

load_dotenv()


def main():
    st.title("📚 Project knowledge")
    st.caption(
        "Originals and `manifest.json` live under `.specify/orchestrator/knowledge/`. "
        "`rag.sqlite` holds embeddings (rebuild after clone if gitignored)."
    )

    if st.session_state.get("selected_project"):
        st.info(f"📂 **Current Project**: {st.session_state.selected_project}")
        if st.session_state.get("project_path"):
            st.caption(f"Path: `{st.session_state.project_path}`")
        st.markdown("---")

    if "project_path" not in st.session_state or not st.session_state.project_path:
        st.warning("⚠️ No project selected. Please select a project first.")
        if st.button("📁 Select Project"):
            st.switch_page("pages/project_selection.py")
        return

    project_path = Path(st.session_state.project_path)
    if not project_path.exists():
        st.error(f"❌ Project path does not exist: {project_path}")
        return

    api_key = st.session_state.get("openai_api_key") or __import__("os").getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key required (sidebar on Interview Chat or `OPENAI_API_KEY` in `.env`).")
        return

    client = OpenAI(api_key=api_key)

    try:
        st.info(f"Vector backend: **{store_backend_label(project_path)}**")
    except Exception as e:
        st.warning(f"Could not open vector store: {e}")

    uploaded = st.file_uploader(
        "Upload documents",
        type=["txt", "md", "pdf", "docx", "csv", "json", "yml", "yaml"],
        accept_multiple_files=True,
    )
    if uploaded:
        for uf in uploaded:
            if uf is None:
                continue
            try:
                with st.spinner(f"Indexing {uf.name}…"):
                    ingest_file(
                        project_path,
                        uf.getvalue(),
                        uf.name,
                        uf.type or "application/octet-stream",
                        client,
                    )
                st.success(f"Indexed: {uf.name}")
            except KnowledgeIngestError as e:
                st.error(f"{uf.name}: {e}")
            except Exception as e:
                st.error(f"{uf.name}: {e}")
        st.rerun()

    docs = list_documents(project_path)
    if not docs:
        st.info("No documents yet. Upload files above.")
        return

    st.subheader("Documents")
    store = KnowledgeRagStore(project_path)
    try:
        chunk_total = store.chunk_count()
    finally:
        store.close()
    st.caption(f"Total indexed chunks in DB: **{chunk_total}**")

    if st.button("Reindex all (re-parse & re-embed every document)", type="secondary"):
        with st.spinner("Reindexing…"):
            ok, errors = reindex_all(project_path, client)
        st.success(f"Reindexed: {ok} document(s).")
        for err in errors:
            st.warning(err)
        st.rerun()

    for rec in docs:
        with st.expander(f"{rec.original_filename} — {rec.ingestion_status}", expanded=False):
            st.text(f"ID: {rec.id}")
            st.text(f"Mode: {rec.ingestion_mode} | Stored: `{rec.stored_relpath}` | SHA256: {rec.sha256[:16]}…")
            if rec.error_message:
                st.error(rec.error_message)

            override = st.selectbox(
                "Override (per document)",
                options=["(auto)", "force_inline", "force_rag"],
                index=(
                    0
                    if rec.user_override_mode is None
                    else (1 if rec.user_override_mode == "force_inline" else 2)
                ),
                key=f"ov_{rec.id}",
            )
            if st.button("Save override", key=f"save_ov_{rec.id}"):
                rec.user_override_mode = (
                    None
                    if override == "(auto)"
                    else (override if override in ("force_inline", "force_rag") else None)
                )
                upsert_document(project_path, rec)
                st.success("Saved.")
                st.rerun()

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Reindex", key=f"reidx_{rec.id}"):
                    try:
                        with st.spinner("Reindexing…"):
                            reindex_document(project_path, rec.id, client)
                        st.success("Done.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with c2:
                path = project_path / ".specify" / "orchestrator" / "knowledge" / rec.stored_relpath
                if path.exists():
                    st.download_button(
                        "Download original",
                        data=path.read_bytes(),
                        file_name=rec.original_filename,
                        key=f"dl_{rec.id}",
                    )
            with c3:
                if st.button("Delete", type="primary", key=f"del_{rec.id}"):
                    delete_document_completely(project_path, rec.id)
                    st.success("Removed.")
                    st.rerun()


main()
