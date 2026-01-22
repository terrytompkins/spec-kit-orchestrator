"""Navigation sidebar component for Spec Kit Orchestrator."""

import streamlit as st


def hide_streamlit_navigation():
    """
    Hide Streamlit's automatic page navigation menu.
    This should be called as early as possible in each page, ideally right after imports.
    """
    st.markdown("""
        <style>
        /* Hide Streamlit's automatic page navigation - applied immediately */
        [data-testid="stSidebarNav"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            overflow: hidden !important;
        }
        /* Also hide any nav links that might appear */
        [data-testid="stSidebarNav"] ul,
        [data-testid="stSidebarNav"] li,
        [data-testid="stSidebarNav"] a {
            display: none !important;
            visibility: hidden !important;
        }
        </style>
        """, unsafe_allow_html=True)


def render_navigation_sidebar():
    """
    Render the navigation sidebar with project status and page navigation buttons.
    This should be called at the start of every page to ensure consistent navigation.
    Note: hide_streamlit_navigation() should be called earlier, right after imports.
    """
    # Initialize session state if needed
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'project_path' not in st.session_state:
        st.session_state.project_path = None
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Show current project status in sidebar
    st.sidebar.markdown("---")
    if st.session_state.selected_project:
        st.sidebar.success(f"📂 **Current Project**\n\n{st.session_state.selected_project}")
        if st.session_state.project_path:
            # Show truncated path if it's long
            path_display = st.session_state.project_path
            if len(path_display) > 40:
                path_display = "..." + path_display[-37:]
            st.sidebar.caption(f"`{path_display}`")
        if st.sidebar.button("🔄 Clear Project", use_container_width=True):
            st.session_state.selected_project = None
            st.session_state.project_path = None
            st.rerun()
    else:
        st.sidebar.info("👈 No project selected")
    st.sidebar.markdown("---")
    
    # Navigation buttons - all pages accessible from sidebar
    st.sidebar.markdown("### Pages")
    
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.switch_page("app.py")
    
    if st.sidebar.button("📁 Select Project", use_container_width=True):
        st.switch_page("pages/project_selection.py")
    
    if st.sidebar.button("➕ New Project", use_container_width=True):
        st.switch_page("pages/project_creation.py")
    
    if st.sidebar.button("🚀 Phase Runner", use_container_width=True):
        st.switch_page("pages/phase_runner.py")
    
    if st.sidebar.button("💬 Interview Chat", use_container_width=True):
        st.switch_page("pages/interview_chat.py")
    
    if st.sidebar.button("📄 Artifact Browser", use_container_width=True):
        st.switch_page("pages/artifact_browser.py")
