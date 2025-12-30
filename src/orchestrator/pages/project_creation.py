"""Project creation page for Spec Kit Orchestrator."""

import streamlit as st
from pathlib import Path
from datetime import datetime

from ..services.config_manager import ConfigManager
from ..services.cli_executor import CLIExecutor, CLIExecutionError
from ..services.run_metadata import RunMetadata
from ..utils.path_validation import validate_path, PathValidationError
from ..models.project import Project
import os


def main():
    """Main project creation page."""
    st.title("➕ Create New Spec Kit Project")
    
    config_manager = ConfigManager()
    base_directory = config_manager.get_base_directory()
    allowed_ai_agents = config_manager.get_allowed_ai_agents()
    
    st.info(f"**Base Directory**: `{base_directory}`\n\nAll projects must be created within this directory.")
    
    # Project creation form
    with st.form("create_project_form"):
        project_name = st.text_input("Project Name", placeholder="my-spec-kit-project")
        parent_directory = st.text_input(
            "Parent Directory",
            placeholder=str(base_directory),
            help=f"Must be within: {base_directory}"
        )
        
        ai_agent = st.selectbox(
            "AI Agent",
            options=allowed_ai_agents,
            help="Select the AI agent to use for Spec Kit commands"
        )
        
        github_token = st.text_input(
            "GitHub Token (Optional)",
            type="password",
            help="Optional GitHub token for Spec Kit initialization"
        )
        
        extra_params = st.text_area(
            "Extra Parameters (Optional)",
            placeholder="--param1 value1 --param2 value2",
            help="Additional parameters to pass to `specify init`"
        )
        
        submitted = st.form_submit_button("Create Project", type="primary")
    
    if submitted:
        # Validate inputs
        errors = []
        
        if not project_name:
            errors.append("Project name is required")
        
        if not parent_directory:
            parent_directory = str(base_directory)
        
        # Validate path
        try:
            validated_path = validate_path(parent_directory, base_directory)
            project_path = validated_path / project_name
        except PathValidationError as e:
            errors.append(f"Invalid path: {str(e)}")
            project_path = None
        
        # Validate AI agent
        if not config_manager.is_ai_agent_allowed(ai_agent):
            errors.append(f"AI agent '{ai_agent}' is not in allowed list")
        
        # Display errors if any
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
            return
        
        # Check if CLI is installed
        executor = CLIExecutor()
        if not executor.check_command_exists('specify'):
            st.error("""
            ❌ **Spec Kit CLI not found**
            
            The `specify` command is not available in your PATH.
            
            Please install Spec Kit following the [official documentation](https://github.com/spec-kit/spec-kit).
            """)
            return
        
        # Execute specify init
        st.subheader("Initializing Project...")
        
        # Build command
        command = ['specify', 'init']
        command.extend(['--ai', ai_agent])
        
        if github_token:
            command.extend(['--github-token', github_token])
        
        if extra_params:
            # Parse extra params (simple space-separated for now)
            import shlex
            try:
                extra_args = shlex.split(extra_params)
                command.extend(extra_args)
            except ValueError as e:
                st.error(f"Invalid extra parameters: {str(e)}")
                return
        
        # Add project name as positional argument if Spec Kit requires it
        # (Adjust based on actual Spec Kit CLI interface)
        command.append(project_name)
        
        # Create output container for streaming
        output_container = st.empty()
        output_lines = []
        
        # Create run metadata manager
        run_metadata = RunMetadata(project_path)
        run_dir = run_metadata.create_run_directory()
        stdout_log_path = run_dir / 'stdout.log'
        stderr_log_path = run_dir / 'stderr.log'
        
        start_timestamp = datetime.now()
        
        # Stream output callback
        def output_callback(line):
            output_lines.append(line)
            with open(stdout_log_path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
            # Update UI incrementally
            output_container.code('\n'.join(output_lines))
        
        def error_callback(line):
            output_lines.append(f"[stderr] {line}")
            with open(stderr_log_path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
            # Update UI incrementally
            output_container.code('\n'.join(output_lines))
        
        # Execute command
        try:
            exit_code, stdout, stderr = executor.execute(
                command,
                working_directory=validated_path,
                output_callback=output_callback,
                error_callback=error_callback
            )
            
            end_timestamp = datetime.now()
            
            # Collect non-secret environment variables
            env_vars = {}
            secret_keywords = ['TOKEN', 'KEY', 'SECRET', 'PASSWORD', 'CREDENTIAL']
            for k, v in os.environ.items():
                if not any(keyword in k.upper() for keyword in secret_keywords):
                    env_vars[k] = v
            
            # Create execution metadata
            metadata = run_metadata.create_metadata(
                phase_name="init",
                command=' '.join(command),
                args=command[1:],  # Exclude 'specify'
                working_directory=validated_path,
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
                st.success(f"✅ Project '{project_name}' created successfully!")
                st.info(f"**Project Path**: `{project_path}`")
                
                # Set project in session state
                st.session_state.selected_project = project_name
                st.session_state.project_path = str(project_path)
                
                st.markdown("### Next Steps")
                st.markdown("""
                1. Navigate to **Phase Runner** to run Spec Kit phases
                2. Or go to **Interview Chat** to generate parameter documents
                """)
            else:
                st.error(f"❌ Project creation failed with exit code {exit_code}")
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
    import os
    main()

