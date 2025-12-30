"""Main Streamlit app entry point for Spec Kit Orchestrator."""

import streamlit as st
from pathlib import Path

# Set page config
st.set_page_config(
    page_title="Spec Kit Orchestrator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'project_path' not in st.session_state:
    st.session_state.project_path = None

# Main title
st.title("🎯 Spec Kit Orchestrator")
st.markdown("A non-technical UI for managing Spec Kit workflows")

# Sidebar navigation
st.sidebar.title("Navigation")

# Note: Streamlit's multi-page support automatically creates navigation
# from files in the pages/ directory. This main app.py serves as the
# home page and can redirect to project selection if no project is selected.

# Check if we're on the home page (no page selected)
if st.sidebar.button("🏠 Home"):
    st.session_state.selected_project = None
    st.rerun()

if st.sidebar.button("📁 Select Project"):
    st.switch_page("pages/project_selection.py")

if st.sidebar.button("➕ New Project"):
    st.switch_page("pages/project_creation.py")

# Main content
if st.session_state.selected_project is None:
    st.info("👈 Select a project from the sidebar or create a new one to get started.")
    st.markdown("""
    ### Getting Started
    
    1. **Select an existing project** from your workspace
    2. **Create a new project** to initialize a new Spec Kit project
    3. **Generate parameters** to create command parameter documents
    4. **Run phases** to execute Spec Kit workflows
    5. **Browse artifacts** to review generated content
    
    See the README.md for detailed setup and configuration instructions.
    """)
else:
    st.success(f"📂 Working with project: {st.session_state.selected_project}")
    st.markdown(f"**Path**: `{st.session_state.project_path}`")
    
    # Quick actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Run Phases"):
            st.switch_page("pages/phase_runner.py")
    
    with col2:
        if st.button("📄 Browse Artifacts"):
            st.switch_page("pages/artifact_browser.py")
    
    with col3:
        if st.button("💬 Generate Parameters"):
            st.switch_page("pages/interview_chat.py")

