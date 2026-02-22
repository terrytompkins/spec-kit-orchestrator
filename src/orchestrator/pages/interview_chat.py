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
    # Which project we've already chosen Resume/Start new for (so we don't show banner again)
    if 'interview_session_resolved_project' not in st.session_state:
        st.session_state.interview_session_resolved_project = None


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
                    st.rerun()
        with col_new:
            if st.button("Start new", key="interview_start_new"):
                st.session_state.chat_messages = []
                st.session_state.interview_complete = False
                st.session_state.generated_parameters = None
                st.session_state.interview_session_resolved_project = str(project_path)
                interview_state_service.save(
                    project_path,
                    [],
                    False,
                    None,
                )
                st.rerun()
        return
    
    # Mark that we've resolved resume/start new for this project (so we don't show banner again)
    st.session_state.interview_session_resolved_project = str(project_path)
    
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
        interview_state_service.save(
            project_path,
            st.session_state.chat_messages,
            st.session_state.interview_complete,
            st.session_state.generated_parameters,
        )
    
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
                interview_state_service.save(project_path, [], False, None)
                st.rerun()
        
        return
    
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
                    # Conduct interview step
                    result = st.session_state.ai_service.conduct_interview_step(
                        st.session_state.chat_messages[:-1],  # All messages except the one we just added
                        prompt
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
                        interview_state_service.save(
                            project_path,
                            st.session_state.chat_messages,
                            True,
                            st.session_state.generated_parameters,
                        )
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
                        interview_state_service.save(
                            project_path,
                            st.session_state.chat_messages,
                            st.session_state.interview_complete,
                            st.session_state.generated_parameters,
                        )
                
                except Exception as e:
                    error_msg = f"❌ Error during interview: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    interview_state_service.save(
                        project_path,
                        st.session_state.chat_messages,
                        st.session_state.interview_complete,
                        st.session_state.generated_parameters,
                    )


# When used with st.navigation(), Streamlit executes this file directly
# so we call main() at module level (not inside if __name__ == "__main__")
main()
