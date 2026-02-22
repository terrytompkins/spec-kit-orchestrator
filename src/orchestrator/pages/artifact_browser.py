"""Artifact browser page for Spec Kit Orchestrator."""

import sys
from pathlib import Path

# Add parent directory to path for imports when running as Streamlit page
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from orchestrator.services.artifact_reader import ArtifactReader
from orchestrator.services.run_metadata import RunMetadata

# Note: render_navigation_sidebar() is called in app.py, so we don't call it here
# to avoid duplication

def main():
    """Main artifact browser page."""
    st.title("📄 Browse Artifacts")
    
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
        st.session_state.project_path = None
        st.session_state.selected_project = None
        return
    
    artifact_reader = ArtifactReader(project_path)
    run_metadata = RunMetadata(project_path)
    
    # Discover artifacts
    artifacts = artifact_reader.discover_artifacts()
    
    # Tabs for artifacts and execution logs
    tab1, tab2 = st.tabs(["📄 Artifacts", "📋 Execution Logs"])
    
    with tab1:
        if not artifacts:
            st.info("""
            **No artifacts found**
            
            Artifacts will appear here after you run Spec Kit phases.
            
            Navigate to **Phase Runner** to execute phases.
            """)
        else:
            st.subheader(f"Available Artifacts ({len(artifacts)})")
            
            # Group artifacts by type
            artifact_types = {}
            for artifact in artifacts:
                if artifact.artifact_type not in artifact_types:
                    artifact_types[artifact.artifact_type] = []
                artifact_types[artifact.artifact_type].append(artifact)
            
            # Display artifacts by type
            for artifact_type, type_artifacts in artifact_types.items():
                with st.expander(f"📄 {artifact_type.title()} ({len(type_artifacts)})", expanded=False):
                    for artifact in type_artifacts:
                        if st.button(f"View: {artifact.file_path.name}", key=f"view_{artifact.file_path}"):
                            st.session_state[f"viewing_{artifact.file_path}"] = True
                        
                        if st.session_state.get(f"viewing_{artifact.file_path}", False):
                            content = artifact.get_content()
                            if content:
                                st.markdown("### Content")
                                st.markdown(content)
                                
                                # Show related artifacts
                                related = artifact_reader.get_related_artifacts(artifact.artifact_type)
                                if related:
                                    st.markdown("### Related Artifacts")
                                    for rel_type, rel_artifact in related.items():
                                        if rel_artifact:
                                            if st.button(f"View {rel_type}", key=f"related_{rel_type}_{artifact.file_path}"):
                                                st.session_state[f"viewing_{rel_artifact.file_path}"] = True
                                                st.rerun()
                            else:
                                st.error("Could not read artifact content")
    
    with tab2:
        st.subheader("Execution History")
        
        runs = run_metadata.list_runs()
        
        if not runs:
            st.info("No execution history found. Run phases to see execution logs here.")
        else:
            st.info(f"Found {len(runs)} execution(s)")
            
            for run_dir in runs:
                try:
                    metadata = run_metadata.load_metadata(run_dir)
                    
                    with st.expander(
                        f"{metadata['phase_name']} - {metadata['status']} - {run_dir.name}",
                        expanded=False
                    ):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Phase**: {metadata['phase_name']}")
                            st.markdown(f"**Status**: {metadata['status']}")
                            st.markdown(f"**Exit Code**: {metadata.get('exit_code', 'N/A')}")
                            st.markdown(f"**Start**: {metadata['start_timestamp']}")
                            if metadata.get('end_timestamp'):
                                st.markdown(f"**End**: {metadata['end_timestamp']}")
                        
                        with col2:
                            if metadata.get('git_commit_hash'):
                                st.markdown(f"**Git Commit**: `{metadata['git_commit_hash'][:8]}`")
                            if metadata.get('inputs_hash'):
                                st.markdown(f"**Inputs Hash**: `{metadata['inputs_hash'][:16]}...`")
                        
                        # View logs
                        if st.button("View Logs", key=f"logs_{run_dir.name}"):
                            st.session_state[f"viewing_logs_{run_dir.name}"] = True
                        
                        if st.session_state.get(f"viewing_logs_{run_dir.name}", False):
                            stdout_log = artifact_reader.read_execution_log(run_dir, 'stdout')
                            stderr_log = artifact_reader.read_execution_log(run_dir, 'stderr')
                            
                            if stdout_log:
                                st.markdown("### stdout")
                                st.code(stdout_log, language='text')
                            
                            if stderr_log:
                                st.markdown("### stderr")
                                st.code(stderr_log, language='text')
                
                except Exception as e:
                    st.error(f"Error loading metadata from {run_dir}: {str(e)}")


# When used with st.navigation(), Streamlit executes this file directly
# so we call main() at module level (not inside if __name__ == "__main__")
main()

