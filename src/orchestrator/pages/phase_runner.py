"""Phase runner page for executing Spec Kit phases."""

import streamlit as st
from pathlib import Path
from datetime import datetime
import os

from ..services.cli_executor import CLIExecutor, CLIExecutionError
from ..services.run_metadata import RunMetadata
from ..services.artifact_reader import ArtifactReader
from ..services.config_manager import ConfigManager


# Phase definitions
PHASES = [
    ('constitution', 'Constitution', 'Establishes project principles'),
    ('specify', 'Specify', 'Creates feature specifications'),
    ('clarify', 'Clarify', 'Resolves ambiguities'),
    ('plan', 'Plan', 'Generates implementation plans'),
    ('tasks', 'Tasks', 'Breaks plans into tasks'),
    ('analyze', 'Analyze', 'Post-tasks verification')
]

# Phase dependencies (which phases must run before this one)
PHASE_DEPENDENCIES = {
    'specify': ['constitution'],
    'clarify': ['specify'],
    'plan': ['specify'],
    'tasks': ['plan'],
    'analyze': ['tasks']
}


def get_phase_status(project_path: Path, phase_name: str, artifact_reader: ArtifactReader) -> str:
    """Get status of a phase based on artifacts and execution history."""
    # Check if artifact exists
    artifact = artifact_reader.read_artifact(phase_name)
    if artifact and artifact.exists():
        return "completed"
    
    # Could check execution history here
    return "not_started"


def check_phase_dependencies(project_path: Path, phase_name: str, artifact_reader: ArtifactReader) -> tuple[bool, List[str]]:
    """
    Check if phase dependencies are met.
    
    Returns:
        Tuple of (dependencies_met, missing_dependencies)
    """
    if phase_name not in PHASE_DEPENDENCIES:
        return True, []
    
    required = PHASE_DEPENDENCIES[phase_name]
    missing = []
    
    for req_phase in required:
        artifact = artifact_reader.read_artifact(req_phase)
        if not artifact or not artifact.exists():
            missing.append(req_phase)
    
    return len(missing) == 0, missing


def main():
    """Main phase runner page."""
    st.title("🚀 Run Spec Kit Phases")
    
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
    
    artifact_reader = ArtifactReader(project_path)
    run_metadata = RunMetadata(project_path)
    executor = CLIExecutor()
    
    # Check if CLI is available
    if not executor.check_command_exists('specify'):
        st.error("""
        ❌ **Spec Kit CLI not found**
        
        The `specify` command is not available in your PATH.
        Please install Spec Kit to continue.
        """)
        return
    
    st.info(f"**Project**: `{project_path.name}`")
    
    # Phase buttons
    st.subheader("Phase Execution")
    
    # Get current status for each phase
    phase_statuses = {}
    for phase_id, phase_name, phase_desc in PHASES:
        phase_statuses[phase_id] = get_phase_status(project_path, phase_id, artifact_reader)
    
    # Display phase buttons
    for phase_id, phase_name, phase_desc in PHASES:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            status = phase_statuses[phase_id]
            status_emoji = {
                'completed': '✅',
                'in_progress': '⏳',
                'failed': '❌',
                'not_started': '⚪'
            }.get(status, '⚪')
            
            st.markdown(f"**{status_emoji} {phase_name}**")
            st.caption(phase_desc)
        
        with col2:
            # Check dependencies
            deps_met, missing = check_phase_dependencies(project_path, phase_id, artifact_reader)
            
            # Disable Analyze until Tasks completes
            disabled = False
            if phase_id == 'analyze' and phase_statuses.get('tasks') != 'completed':
                disabled = True
                st.caption("⏸️ Wait for Tasks")
            elif not deps_met:
                disabled = True
                st.caption(f"⚠️ Needs: {', '.join(missing)}")
            
            button_key = f"run_{phase_id}"
            if st.button(f"Run {phase_name}", key=button_key, disabled=disabled):
                st.session_state[f"running_{phase_id}"] = True
        
        with col3:
            if phase_statuses[phase_id] == 'completed':
                artifact = artifact_reader.read_artifact(phase_id)
                if artifact:
                    if st.button("View", key=f"view_{phase_id}"):
                        st.switch_page("pages/artifact_browser.py")
    
    # Handle phase execution
    for phase_id, phase_name, phase_desc in PHASES:
        if st.session_state.get(f"running_{phase_id}", False):
            st.session_state[f"running_{phase_id}"] = False
            
            # Check dependencies and warn if needed
            deps_met, missing = check_phase_dependencies(project_path, phase_id, artifact_reader)
            
            if not deps_met:
                st.warning(f"⚠️ **Dependencies not met**: This phase requires {', '.join(missing)} to be completed first.")
                if not st.button("Proceed Anyway", key=f"proceed_{phase_id}"):
                    continue
            
            # Execute phase
            st.subheader(f"Running: {phase_name}")
            
            # Build command
            command = ['specify', phase_id]
            
            # Create output container
            output_container = st.empty()
            output_lines = []
            
            # Create run directory
            run_dir = run_metadata.create_run_directory()
            stdout_log_path = run_dir / 'stdout.log'
            stderr_log_path = run_dir / 'stderr.log'
            
            start_timestamp = datetime.now()
            
            # Stream output
            def output_callback(line):
                output_lines.append(line)
                with open(stdout_log_path, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
                output_container.code('\n'.join(output_lines))
            
            def error_callback(line):
                output_lines.append(f"[stderr] {line}")
                with open(stderr_log_path, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
                output_container.code('\n'.join(output_lines))
            
            try:
                # Collect non-secret environment variables
                env_vars = {}
                secret_keywords = ['TOKEN', 'KEY', 'SECRET', 'PASSWORD', 'CREDENTIAL']
                for k, v in os.environ.items():
                    if not any(keyword in k.upper() for keyword in secret_keywords):
                        env_vars[k] = v
                
                exit_code, stdout, stderr = executor.execute(
                    command,
                    working_directory=project_path,
                    output_callback=output_callback,
                    error_callback=error_callback
                )
                
                end_timestamp = datetime.now()
                
                # Create metadata
                metadata = run_metadata.create_metadata(
                    phase_name=phase_id,
                    command=' '.join(command),
                    args=command[1:],
                    working_directory=project_path,
                    environment_vars=env_vars,
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp,
                    exit_code=exit_code,
                    stdout_log_path=stdout_log_path,
                    stderr_log_path=stderr_log_path,
                    run_dir=run_dir
                )
                
                run_metadata.save_metadata(metadata, run_dir)
                
                if exit_code == 0:
                    st.success(f"✅ {phase_name} completed successfully!")
                    
                    # Check if artifact was created
                    artifact = artifact_reader.read_artifact(phase_id)
                    if artifact and artifact.exists():
                        st.info(f"📄 Artifact generated: `{artifact.file_path.relative_to(project_path)}`")
                        if st.button(f"View {phase_name} Artifact", key=f"view_artifact_{phase_id}"):
                            st.switch_page("pages/artifact_browser.py")
                else:
                    st.error(f"❌ {phase_name} failed with exit code {exit_code}")
                    if stderr:
                        with st.expander("Error Details"):
                            st.code('\n'.join(stderr))
            
            except CLIExecutionError as e:
                st.error(f"❌ Execution error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    main()

