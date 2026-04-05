"""Interview chat page for generating parameter documents."""

import sys
from pathlib import Path

# Add parent directory to path for imports when running as Streamlit page
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
from datetime import datetime as dt_parse
import streamlit as st
from dotenv import load_dotenv
from orchestrator.services.parameter_generator import ParameterGenerator
from orchestrator.services.ai_interview import AIInterviewService
from orchestrator.services import interview_state as interview_state_service
from orchestrator.services.knowledge_context import build_reference_bundle, retrieval_query_from_turn
from orchestrator.services.knowledge_ingest import KnowledgeIngestError, ingest_file
from orchestrator.services.knowledge_manifest import list_documents
from orchestrator.services.knowledge_rag_store import store_backend_label

# Note: render_navigation_sidebar() is called in app.py, so we don't call it here
# to avoid duplication

# Load environment variables from .env file
load_dotenv()


def initialize_chat_state():
    """Initialize chat state in session state."""
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'interview_complete' not in st.session_state:
        st.session_state.interview_complete = False
    if 'generated_parameters' not in st.session_state:
        st.session_state.generated_parameters = None
    if 'ai_service' not in st.session_state:
        st.session_state.ai_service = None
    # Which project the current in-memory chat state belongs to
    if 'interview_chat_project' not in st.session_state:
        st.session_state.interview_chat_project = None
    # Which project we've already chosen Resume/Start new for (so we don't show banner again)
    if 'interview_session_resolved_project' not in st.session_state:
        st.session_state.interview_session_resolved_project = None


def _indexed_doc_ids(project_path: Path) -> list[str]:
    return [d.id for d in list_documents(project_path) if d.ingestion_status == "indexed"]


def _save_interview_state(project_path: Path) -> None:
    interview_state_service.save(
        project_path,
        st.session_state.chat_messages,
        st.session_state.interview_complete,
        st.session_state.generated_parameters,
        active_document_ids=st.session_state.get("knowledge_active_ids", []),
        session_focus=st.session_state.get("knowledge_session_focus", ""),
        knowledge_reference_mode=st.session_state.get("knowledge_reference_mode", "auto"),
    )


def _hydrate_knowledge_session(project_path: Path) -> None:
    state = interview_state_service.load(project_path)
    indexed = _indexed_doc_ids(project_path)
    if state and state.get("active_document_ids") is not None:
        ads = state.get("active_document_ids") or []
        valid = [x for x in ads if x in indexed]
        st.session_state.knowledge_active_ids = valid if valid else list(indexed)
        st.session_state.knowledge_session_focus = state.get("session_focus", "") or ""
        krm = state.get("knowledge_reference_mode", "auto")
        st.session_state.knowledge_reference_mode = (
            krm if krm in ("auto", "prefer_inline", "rag_only") else "auto"
        )
    else:
        st.session_state.knowledge_active_ids = list(indexed)
        st.session_state.knowledge_session_focus = ""
        st.session_state.knowledge_reference_mode = "auto"


def main():
    """Main interview chat page."""
    initialize_chat_state()
    
    st.title("💬 Generate Parameter Documents")
    
    # Show current project header
    if st.session_state.get('selected_project'):
        st.info(f"📂 **Current Project**: {st.session_state.selected_project}")
        if st.session_state.get('project_path'):
            st.caption(f"Path: `{st.session_state.project_path}`")
        st.markdown("---")
    
    # Check if project is selected
    if 'project_path' not in st.session_state or not st.session_state.project_path:
        st.warning("⚠️ No project selected. Please select a project first.")
        if st.button("📁 Select Project"):
            st.switch_page("pages/project_selection.py")
        return
    
    project_path = Path(st.session_state.project_path)
    
    if not project_path.exists():
        st.error(f"❌ Project path does not exist: {project_path}")
        return
    
    # When user switches to a different project, clear in-memory chat state so we
    # don't show the previous project's conversation
    current_project_key = str(project_path)
    if st.session_state.interview_chat_project != current_project_key:
        st.session_state.chat_messages = []
        st.session_state.interview_complete = False
        st.session_state.generated_parameters = None
        st.session_state.interview_chat_project = current_project_key
        st.session_state.interview_session_resolved_project = None
        st.session_state._knowledge_hydrated_key = None
    
    generator = ParameterGenerator(project_path)
    
    # Chat state already initialized at the start of main()
    
    # Check for API key: first from environment variable (.env file), then sidebar input, then session state
    env_api_key = os.getenv('OPENAI_API_KEY')
    session_api_key = st.session_state.get('openai_api_key')
    
    # Show indicator if API key is loaded from .env file
    if env_api_key:
        st.sidebar.success("✅ API key loaded from .env file")
    
    # Sidebar input for API key (allows override)
    sidebar_api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        help="Enter your OpenAI API key to enable AI-powered interview. The app will first check for OPENAI_API_KEY in .env file.",
        value=session_api_key or ''
    )
    
    # Use API key in priority order: env var > sidebar input > session state
    api_key = env_api_key or sidebar_api_key or session_api_key
    
    # Store sidebar input in session state if provided
    if sidebar_api_key:
        st.session_state.openai_api_key = sidebar_api_key
    
    # Initialize AI service if API key is available
    use_ai_chat = False
    if api_key:
        try:
            if st.session_state.ai_service is None or st.session_state.get('last_api_key') != api_key:
                st.session_state.ai_service = AIInterviewService(api_key=api_key)
                st.session_state.last_api_key = api_key
            use_ai_chat = True
        except ValueError as e:
            st.sidebar.error(f"⚠️ {str(e)}")
            use_ai_chat = False
        except Exception as e:
            st.sidebar.error(f"⚠️ Error initializing AI service: {str(e)}")
            use_ai_chat = False
    
    # Mode selection
    if not use_ai_chat:
        st.info("""
        **Parameter Document Generation**
        
        To use the AI-powered interview chat, please provide your OpenAI API key in the sidebar.
        Alternatively, you can use the form-based approach below.
        """)
        
        # Show form-based approach
        with st.expander("📝 Form-Based Parameter Entry", expanded=True):
            with st.form("parameter_form"):
                st.subheader("Project Information")
                
                project_description = st.text_area(
                    "Project/Feature Description",
                    placeholder="Describe what you want to build...",
                    height=100
                )
                
                st.subheader("Phase Parameters")
                
                # Collect parameters for each phase
                parameters = {}
                
                for phase_id, phase_name, phase_desc in [
                    ('constitution', 'Constitution', 'Project principles and governance'),
                    ('specify', 'Specify', 'Feature specification details'),
                    ('clarify', 'Clarify', 'Clarification questions'),
                    ('plan', 'Plan', 'Implementation planning context'),
                    ('tasks', 'Tasks', 'Task breakdown requirements'),
                    ('analyze', 'Analyze', 'Analysis focus areas')
                ]:
                    with st.expander(f"{phase_name} Phase Parameters", expanded=(phase_id == 'constitution')):
                        phase_params = {}
                        
                        # Common parameter: description
                        phase_params['description'] = st.text_area(
                            f"{phase_name} Description",
                            placeholder=f"Parameters for {phase_name} phase...",
                            key=f"{phase_id}_desc",
                            height=80
                        )
                        
                        # Store parameters
                        parameters[phase_id] = {
                            'command': f'speckit.{phase_id}',
                            'parameters': phase_params
                        }
                
                submitted = st.form_submit_button("Generate Parameter Documents", type="primary")
            
            if submitted:
                if not project_description:
                    st.warning("⚠️ Please provide a project description.")
                else:
                    # Validate parameters
                    is_valid, missing = generator.validate_parameters(parameters)
                    if not is_valid:
                        st.warning(f"⚠️ Missing parameters for phases: {', '.join(missing)}")
                        st.info("You can leave phases empty if you'll fill them in later, but all phases should have at least a description.")
                    
                    # Generate documents
                    with st.spinner("Generating parameter documents..."):
                        try:
                            markdown_path, yaml_path, backup_md, backup_yml = generator.save_parameter_documents(
                                parameters,
                                create_backups=True
                            )
                            
                            st.success("✅ Parameter documents generated successfully!")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Markdown**: `{markdown_path.relative_to(project_path)}`")
                            with col2:
                                st.markdown(f"**YAML**: `{yaml_path.relative_to(project_path)}`")
                            
                            if backup_md or backup_yml:
                                st.info("📦 Backups created for existing files (if any)")
                                if backup_md:
                                    st.caption(f"Backup: `{backup_md.relative_to(project_path)}`")
                                if backup_yml:
                                    st.caption(f"Backup: `{backup_yml.relative_to(project_path)}`")
                            
                            # Show preview
                            with st.expander("Preview Markdown Document"):
                                content = markdown_path.read_text(encoding='utf-8')
                                st.markdown(content)
                            
                            st.markdown("### Next Steps")
                            st.markdown("""
                            1. Review the generated parameter documents
                            2. Navigate to **Phase Runner** to execute Spec Kit phases
                            3. Use the parameter documents as reference when running phases
                            """)
                        
                        except Exception as e:
                            st.error(f"❌ Error generating documents: {str(e)}")
                            import traceback
                            with st.expander("Error Details"):
                                st.code(traceback.format_exc())
        return
    
    # Offer to resume if this project has a saved session and we haven't chosen yet for this project
    resolved_for = st.session_state.get("interview_session_resolved_project")
    if resolved_for != str(project_path) and interview_state_service.has_resumable_session(project_path):
        saved = interview_state_service.load(project_path)
        saved_at = saved.get("saved_at") if saved else None
        if saved_at:
            try:
                dt = dt_parse.fromisoformat(saved_at.replace("Z", "+00:00"))
                saved_at_label = dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                saved_at_label = saved_at
        else:
            saved_at_label = "previously"
        st.warning(f"**Saved session found** (saved {saved_at_label}). Resume or start a new interview?")
        col_resume, col_new = st.columns(2)
        with col_resume:
            if st.button("Resume", key="interview_resume"):
                state = interview_state_service.load(project_path)
                if state:
                    st.session_state.chat_messages = state.get("chat_messages") or []
                    st.session_state.interview_complete = state.get("interview_complete", False)
                    st.session_state.generated_parameters = state.get("generated_parameters")
                    st.session_state.interview_session_resolved_project = str(project_path)
                    indexed = _indexed_doc_ids(project_path)
                    ads = state.get("active_document_ids") or []
                    st.session_state.knowledge_active_ids = [x for x in ads if x in indexed] or list(
                        indexed
                    )
                    st.session_state.knowledge_session_focus = state.get("session_focus", "") or ""
                    krm = state.get("knowledge_reference_mode", "auto")
                    st.session_state.knowledge_reference_mode = (
                        krm if krm in ("auto", "prefer_inline", "rag_only") else "auto"
                    )
                    st.session_state._knowledge_hydrated_key = str(project_path)
                    st.rerun()
        with col_new:
            if st.button("Start new", key="interview_start_new"):
                st.session_state.chat_messages = []
                st.session_state.interview_complete = False
                st.session_state.generated_parameters = None
                st.session_state.interview_session_resolved_project = str(project_path)
                st.session_state.knowledge_active_ids = _indexed_doc_ids(project_path)
                st.session_state.knowledge_session_focus = ""
                st.session_state.knowledge_reference_mode = "auto"
                st.session_state._knowledge_hydrated_key = str(project_path)
                interview_state_service.save(
                    project_path,
                    [],
                    False,
                    None,
                    active_document_ids=st.session_state.knowledge_active_ids,
                    session_focus="",
                    knowledge_reference_mode="auto",
                )
                st.rerun()
        return
    
    # Mark that we've resolved resume/start new for this project (so we don't show banner again)
    st.session_state.interview_session_resolved_project = str(project_path)

    if st.session_state.get("_knowledge_hydrated_key") != str(project_path):
        st.session_state._knowledge_hydrated_key = str(project_path)
        _hydrate_knowledge_session(project_path)

    with st.expander("📎 Project knowledge (uploads & RAG)", expanded=False):
        st.caption(
            "Files are stored under `.specify/orchestrator/knowledge/` in this project (suitable to commit). "
            "Embeddings live in `rag.sqlite` (often gitignored—reindex from **Project knowledge** page after clone). "
            "Content may be sent to OpenAI for chat and embeddings."
        )
        try:
            st.caption(f"Vector backend: **{store_backend_label(project_path)}**")
        except Exception:
            pass
        uploaded = st.file_uploader(
            "Add documents",
            type=["txt", "md", "pdf", "docx", "csv", "json", "yml", "yaml"],
            accept_multiple_files=True,
            help="Drag and drop or browse. Supported: .txt, .md, .pdf, .docx, and common text configs.",
        )
        if uploaded:
            for uf in uploaded:
                if uf is None:
                    continue
                try:
                    data = uf.getvalue()
                    with st.spinner(f"Indexing {uf.name}…"):
                        ingest_file(
                            project_path,
                            data,
                            uf.name,
                            uf.type or "application/octet-stream",
                            st.session_state.ai_service.client,
                        )
                    st.success(f"Indexed: {uf.name}")
                except KnowledgeIngestError as e:
                    st.error(f"{uf.name}: {e}")
                except Exception as e:
                    st.error(f"{uf.name}: {e}")
            st.session_state.knowledge_active_ids = _indexed_doc_ids(project_path)
            st.rerun()

        all_docs = list_documents(project_path)
        indexed = [d for d in all_docs if d.ingestion_status == "indexed"]
        if indexed:
            labels = {d.id: f"{d.original_filename} ({d.ingestion_mode})" for d in indexed}
            valid_sel = [x for x in st.session_state.get("knowledge_active_ids", []) if x in labels]
            chosen = st.multiselect(
                "Active documents for this interview",
                options=list(labels.keys()),
                default=valid_sel or list(labels.keys()),
                format_func=lambda i: labels.get(i, i),
                help="Only selected documents are used for inline text and retrieval.",
                key=f"knowledge_active_ms_{str(project_path)}",
            )
            st.session_state.knowledge_active_ids = chosen
            _modes = ("auto", "prefer_inline", "rag_only")
            _cur = st.session_state.get("knowledge_reference_mode", "auto")
            if _cur not in _modes:
                _cur = "auto"
            st.session_state.knowledge_reference_mode = st.radio(
                "Reference mode (session)",
                options=list(_modes),
                format_func=lambda x: {
                    "auto": "Auto (small docs inline, large via search)",
                    "prefer_inline": "Prefer full text in context (truncates if needed)",
                    "rag_only": "Retrieval only (no full-document inline)",
                }[x],
                index=_modes.index(_cur),
                horizontal=True,
            )
            st.session_state.knowledge_session_focus = st.text_input(
                "Session focus (optional)",
                value=st.session_state.get("knowledge_session_focus", ""),
                placeholder="e.g. Current feature: checkout — ignore HR handbook sections",
                help="Free-text hint; stored with your interview state. The model sees your chat first—use this to steer emphasis.",
            )
            if st.session_state.knowledge_session_focus.strip():
                st.caption("Focus hint is saved with the session; chat remains the main source of truth.")
        else:
            st.session_state.knowledge_active_ids = []
        if st.button("Open Project knowledge manager →", key="open_knowledge_mgr"):
            st.switch_page("pages/knowledge.py")

    # AI Chat Interface
    st.info("""
    **AI-Powered Interview Chat**
    
    I'll conduct a thorough interview, asking deep, probing questions about your project or feature to understand all the nuances and details. 
    This will help generate comprehensive, high-quality Spec Kit command parameter documents for all phases.
    
    **Note**: The interview will ask 8-12 questions to gather comprehensive information. Please provide detailed answers for best results.
    
    Your session is **auto-saved** after each exchange so you can resume later or on another computer. See **docs/interview-session-persistence.md** for details.
    """)
    
    # Initialize conversation if empty
    if len(st.session_state.chat_messages) == 0:
        initial_question = st.session_state.ai_service.get_initial_question()
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": initial_question
        })
        _save_interview_state(project_path)
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # If interview is complete, show parameters and generation option
    if st.session_state.interview_complete and st.session_state.generated_parameters:
        st.success("✅ Interview complete! Ready to generate parameter documents.")
        
        with st.expander("📋 Review Generated Parameters"):
            for phase_id, phase_data in st.session_state.generated_parameters.items():
                st.markdown(f"### {phase_id.title()} Phase")
                st.json(phase_data)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Generate Parameter Documents", type="primary"):
                with st.spinner("Generating parameter documents..."):
                    try:
                        markdown_path, yaml_path, backup_md, backup_yml = generator.save_parameter_documents(
                            st.session_state.generated_parameters,
                            create_backups=True
                        )
                        
                        st.success("✅ Parameter documents generated successfully!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Markdown**: `{markdown_path.relative_to(project_path)}`")
                        with col2:
                            st.markdown(f"**YAML**: `{yaml_path.relative_to(project_path)}`")
                        
                        if backup_md or backup_yml:
                            st.info("📦 Backups created for existing files (if any)")
                            if backup_md:
                                st.caption(f"Backup: `{backup_md.relative_to(project_path)}`")
                            if backup_yml:
                                st.caption(f"Backup: `{backup_yml.relative_to(project_path)}`")
                        
                        # Show preview
                        with st.expander("Preview Markdown Document"):
                            content = markdown_path.read_text(encoding='utf-8')
                            st.markdown(content)
                        
                        st.markdown("### Next Steps")
                        st.markdown("""
                        1. Review the generated parameter documents
                        2. Navigate to **Phase Runner** to execute Spec Kit phases
                        3. Use the parameter documents as reference when running phases
                        """)
                    
                    except Exception as e:
                        st.error(f"❌ Error generating documents: {str(e)}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())
        
        with col2:
            if st.button("🔄 Start New Interview"):
                st.session_state.chat_messages = []
                st.session_state.interview_complete = False
                st.session_state.generated_parameters = None
                st.session_state.knowledge_active_ids = _indexed_doc_ids(project_path)
                st.session_state.knowledge_session_focus = ""
                st.session_state.knowledge_reference_mode = "auto"
                interview_state_service.save(
                    project_path,
                    [],
                    False,
                    None,
                    active_document_ids=st.session_state.knowledge_active_ids,
                    session_focus="",
                    knowledge_reference_mode="auto",
                )
                st.rerun()
        
        return

    # Manual extraction: assistant may have written phase text in chat without triggering auto-detection
    def _meaningful_user_turns(msgs: list) -> int:
        return sum(
            1
            for m in msgs
            if m.get("role") == "user" and len((m.get("content") or "").strip()) > 20
        )

    if (
        not st.session_state.interview_complete
        and _meaningful_user_turns(st.session_state.chat_messages) >= 6
    ):
        with st.expander("Parameters not finalized automatically?", expanded=False):
            st.caption(
                "If the assistant already wrote Spec Kit phase content in the chat but **Command Parameters** is still empty, "
                "run structured extraction here (one OpenAI call). This saves `generated_parameters` to your project state."
            )
            if st.button("Extract parameters from conversation now", type="secondary"):
                with st.spinner("Extracting parameters from transcript..."):
                    try:
                        tail = st.session_state.chat_messages[-12:]
                        ext_q = "\n".join(
                            (m.get("content") or "") for m in tail if m.get("role") == "user"
                        )[-8000:]
                        ref_bundle = build_reference_bundle(
                            project_path,
                            st.session_state.get("knowledge_active_ids", []),
                            st.session_state.get("knowledge_reference_mode", "auto"),
                            ext_q or "spec kit parameters interview",
                            st.session_state.ai_service.client,
                            session_focus=st.session_state.get("knowledge_session_focus", ""),
                        )
                        params = st.session_state.ai_service.extract_parameters_from_transcript(
                            st.session_state.chat_messages,
                            reference_bundle=ref_bundle or None,
                        )
                        st.session_state.generated_parameters = params
                        st.session_state.interview_complete = True
                        _save_interview_state(project_path)
                        st.success("Parameters extracted and saved. Open **Command Parameters** to review.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Extraction failed: {e}")
    
    # Chat input
    if prompt := st.chat_input("Type your response here..."):
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    ref_query = retrieval_query_from_turn(
                        prompt, st.session_state.chat_messages[:-1]
                    )
                    ref_bundle = build_reference_bundle(
                        project_path,
                        st.session_state.get("knowledge_active_ids", []),
                        st.session_state.get("knowledge_reference_mode", "auto"),
                        ref_query,
                        st.session_state.ai_service.client,
                        session_focus=st.session_state.get("knowledge_session_focus", ""),
                    )
                    result = st.session_state.ai_service.conduct_interview_step(
                        st.session_state.chat_messages[:-1],
                        prompt,
                        reference_bundle=ref_bundle or None,
                    )
                    
                    if result["is_complete"]:
                        # Interview is complete
                        if result.get("final_message"):
                            st.markdown(result["final_message"])
                            st.session_state.chat_messages.append({
                                "role": "assistant",
                                "content": result["final_message"]
                            })
                        
                        st.session_state.generated_parameters = result["parameters"]
                        st.session_state.interview_complete = True
                        _save_interview_state(project_path)
                        st.success("✅ I've gathered enough information. Ready to generate parameters!")
                        st.rerun()
                    else:
                        # Continue interview
                        question = result["question"]
                        st.markdown(question)
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": question
                        })
                        _save_interview_state(project_path)
                
                except Exception as e:
                    error_msg = f"❌ Error during interview: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    _save_interview_state(project_path)


# When used with st.navigation(), Streamlit executes this file directly
# so we call main() at module level (not inside if __name__ == "__main__")
main()
