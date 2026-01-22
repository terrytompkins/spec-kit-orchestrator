"""Project creation page for Spec Kit Orchestrator."""

import sys
from pathlib import Path

# Add parent directory to path for imports when running as Streamlit page
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from orchestrator.utils.navigation import hide_streamlit_navigation

# Hide Streamlit navigation immediately to prevent flash
hide_streamlit_navigation()

from datetime import datetime
from orchestrator.services.config_manager import ConfigManager
from orchestrator.services.cli_executor import CLIExecutor, CLIExecutionError
from orchestrator.services.run_metadata import RunMetadata
from orchestrator.utils.path_validation import validate_path, PathValidationError
from orchestrator.models.project import Project
from orchestrator.utils.navigation import render_navigation_sidebar
import os


def main():
    """Main project creation page."""
    # Render navigation sidebar
    render_navigation_sidebar()
    
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
            "GitHub Token",
            type="password",
            help="GitHub token for Spec Kit initialization. Required to fetch release information from GitHub API. You can also set GH_TOKEN or GITHUB_TOKEN environment variable.",
            placeholder="Enter token or leave empty to use GH_TOKEN/GITHUB_TOKEN env var"
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
        
        # Check if project directory already exists and has content
        if project_path and project_path.exists():
            # Check if directory has any content (excluding hidden files like .specify from failed attempts)
            dir_contents = [item for item in project_path.iterdir() if not item.name.startswith('.')]
            if dir_contents:
                errors.append(f"Directory '{project_name}' already exists and contains files. Please choose a different project name or remove the existing directory.")
            # If it only has hidden files (like .specify from a previous failed attempt), we'll clean it up
        
        # Validate AI agent
        if not config_manager.is_ai_agent_allowed(ai_agent):
            errors.append(f"AI agent '{ai_agent}' is not in allowed list")
        
        # Check if GitHub token is available (from form or environment)
        if not github_token:
            github_token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
            if github_token:
                st.info("ℹ️ Using GitHub token from environment variable (GH_TOKEN or GITHUB_TOKEN)")
            else:
                st.warning("⚠️ **Warning**: No GitHub token provided. Spec Kit initialization may fail when fetching release information from GitHub API. Consider providing a token or setting GH_TOKEN/GITHUB_TOKEN environment variable.")
                # Don't block execution, but warn the user
        
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
            
            Please install Spec Kit following the [official documentation](https://github.com/github/spec-kit).
            """)
            return
        
        # Execute specify init
        st.subheader("Initializing Project...")
        
        # Clean up any leftover directories/files from previous failed attempts
        # specify init requires an empty directory (or will prompt for confirmation)
        if project_path.exists():
            import shutil
            # Remove the entire directory to ensure it's completely clean
            shutil.rmtree(project_path)
        
        # Create project directory (now guaranteed to be empty)
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Build command - specify init requires either a project name, '.', or --here flag
        # Since we're running inside the project directory, we'll use --here
        command = ['specify', 'init', '--here']
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
        
        # Create temporary log files in parent directory to avoid making project directory non-empty
        # We'll move them to the proper location after specify init completes
        import tempfile
        temp_dir = Path(tempfile.mkdtemp(prefix='spec-kit-init-'))
        temp_stdout_log = temp_dir / 'stdout.log'
        temp_stderr_log = temp_dir / 'stderr.log'
        temp_stdout_log.touch()
        temp_stderr_log.touch()
        
        start_timestamp = datetime.now()
        
        # Stream output callback - only collect data, don't update UI from thread
        def output_callback(line):
            with open(temp_stdout_log, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        
        def error_callback(line):
            with open(temp_stderr_log, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        
        # Execute command with status indicator
        exit_code = None
        stdout = []
        stderr = []
        
        # Show a note that this may take a while
        st.info("⏳ Initializing project... This may take a minute. Output will be displayed when complete.")
        
        with st.status("Initializing project...", expanded=True) as status:
            try:
                exit_code, stdout, stderr = executor.execute(
                    command,
                    working_directory=project_path,  # Run inside the project directory  # Run inside the project directory
                    output_callback=output_callback,
                    error_callback=error_callback
                )
                
                # Display output after execution completes (in main thread)
                # Use a container with constrained width to prevent horizontal stretching
                if stdout:
                    with st.container():
                        st.markdown("**Command Output:**")
                        # Use markdown code block with language for better formatting
                        st.markdown(f"```\n{chr(10).join(stdout)}\n```")
                if stderr:
                    st.warning("Errors occurred:")
                    with st.container():
                        st.markdown(f"```\n{chr(10).join(stderr)}\n```")
                end_timestamp = datetime.now()
                
                # Now that specify init has completed, create run metadata in the proper location
                run_metadata = RunMetadata(project_path)
                run_dir = run_metadata.create_run_directory()
                stdout_log_path = run_dir / 'stdout.log'
                stderr_log_path = run_dir / 'stderr.log'
                
                # Move temporary log files to proper location
                import shutil
                if temp_stdout_log.exists():
                    shutil.move(str(temp_stdout_log), str(stdout_log_path))
                if temp_stderr_log.exists():
                    shutil.move(str(temp_stderr_log), str(stderr_log_path))
                
                # Clean up temp directory
                try:
                    temp_dir.rmdir()
                except OSError:
                    pass  # Directory not empty, that's okay
                
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
                    status.update(label="✅ Project created successfully!", state="complete")
                else:
                    status.update(label=f"❌ Project creation failed (exit code {exit_code})", state="error")
            
            except CLIExecutionError as e:
                exit_code = -1
                status.update(label=f"❌ Execution error: {str(e)}", state="error")
                st.error(f"Execution error: {str(e)}")
            except Exception as e:
                exit_code = -1
                status.update(label=f"❌ Unexpected error: {str(e)}", state="error")
                import traceback
                st.error(f"Unexpected error: {str(e)}")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
        
        # Display results after status context (in main thread)
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
        elif exit_code is not None:
            st.error(f"❌ Project creation failed with exit code {exit_code}")


if __name__ == "__main__":
    import os
    main()

