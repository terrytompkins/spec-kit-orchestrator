"""Project selection page for Spec Kit Orchestrator."""

import streamlit as st
from pathlib import Path

from ..services.project_discovery import ProjectDiscovery
from ..services.config_manager import ConfigManager


def main():
    """Main project selection page."""
    st.title("📁 Select Project")
    
    config_manager = ConfigManager()
    discovery = ProjectDiscovery(config_manager)
    
    # Discover projects
    with st.spinner("Discovering projects..."):
        projects = discovery.discover_projects()
    
    if not projects:
        st.info("""
        **No projects found**
        
        No Spec Kit projects were found in the configured workspace directory.
        
        **Workspace Directory**: `{base_dir}`
        
        To create a new project, navigate to **New Project** from the sidebar.
        """.format(base_dir=config_manager.get_base_directory()))
        
        if st.button("➕ Create New Project"):
            st.switch_page("pages/project_creation.py")
        return
    
    st.success(f"Found {len(projects)} project(s)")
    
    # Display project list
    st.subheader("Available Projects")
    
    for project in projects:
        with st.expander(f"📂 {project.name}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Path**: `{project.path}`")
                st.markdown(f"**Last Modified**: {project.init_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Get project state
                state = discovery.get_project_state(project.path)
                if state['artifacts']:
                    st.markdown(f"**Artifacts**: {', '.join(state['artifacts'])}")
                if state['last_execution']:
                    st.markdown(f"**Last Execution**: {state['last_execution']}")
            
            with col2:
                if st.button("Select", key=f"select_{project.name}"):
                    st.session_state.selected_project = project.name
                    st.session_state.project_path = str(project.path)
                    st.success(f"✅ Selected project: {project.name}")
                    st.rerun()
    
    # Quick select dropdown
    st.subheader("Quick Select")
    project_names = [p.name for p in projects]
    selected_name = st.selectbox("Select a project", options=project_names)
    
    if st.button("Load Project", type="primary"):
        selected_project = next(p for p in projects if p.name == selected_name)
        st.session_state.selected_project = selected_project.name
        st.session_state.project_path = str(selected_project.path)
        st.success(f"✅ Loaded project: {selected_project.name}")
        st.rerun()


if __name__ == "__main__":
    main()

