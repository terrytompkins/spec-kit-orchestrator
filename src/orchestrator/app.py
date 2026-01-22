"""Main Streamlit app entry point for Spec Kit Orchestrator."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src/ directory to path for imports
# This allows imports like "from orchestrator.utils.navigation import ..."
# app.py is at src/orchestrator/app.py, so parent.parent is src/
src_path = Path(__file__).parent.parent.resolve()
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Load environment variables from .env file if it exists
# This must be done before any other imports that might use environment variables
load_dotenv()

import streamlit as st

# Set page config
st.set_page_config(
    page_title="Spec Kit Orchestrator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Initialize session state
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'project_path' not in st.session_state:
    st.session_state.project_path = None

# Import navigation component
from orchestrator.utils.navigation import render_navigation_sidebar


def home_page():
    """Home page content."""
    # Main title
    st.title("🎯 Spec Kit Orchestrator")
    st.markdown("A non-technical UI for managing Spec Kit workflows")

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


# Define pages using st.Page API
# This allows custom labels and icons without emojis in filenames
# Use absolute paths to ensure files are found regardless of working directory
pages_dir = Path(__file__).parent / "pages"

pages = [
    st.Page(
        home_page,
        title="Home",
        icon="🏠",
        default=True  # This will be the default/home page
    ),
    st.Page(
        str((pages_dir / "project_selection.py").resolve()),
        title="Select Project",
        icon="📁"
    ),
    st.Page(
        str((pages_dir / "project_creation.py").resolve()),
        title="New Project",
        icon="➕"
    ),
    st.Page(
        str((pages_dir / "phase_runner.py").resolve()),
        title="Phase Runner",
        icon="🚀"
    ),
    st.Page(
        str((pages_dir / "interview_chat.py").resolve()),
        title="Interview Chat",
        icon="💬"
    ),
    st.Page(
        str((pages_dir / "artifact_browser.py").resolve()),
        title="Artifact Browser",
        icon="📄"
    ),
]

# Render project status in sidebar first (will appear above navigation)
render_navigation_sidebar()

# Create navigation with native sidebar navigation
# This will show the pages with custom titles/icons we defined above
# The navigation will appear below the project status in the sidebar
nav = st.navigation(pages, position="sidebar")

# Run the selected page
nav.run()

