"""Navigation sidebar component for Spec Kit Orchestrator."""

import streamlit as st
from pathlib import Path


def render_navigation_sidebar():
    """
    Render the navigation sidebar with project status.
    This should be called at the start of every page to ensure consistent navigation.
    Note: Native Streamlit navigation (from st.navigation) is handled separately in app.py.
    """
    # Initialize session state if needed
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'project_path' not in st.session_state:
        st.session_state.project_path = None
    
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
