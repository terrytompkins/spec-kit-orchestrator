"""Unit tests for CLI executor."""

import pytest
from pathlib import Path
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock

from src.orchestrator.services.cli_executor import CLIExecutor, CLIExecutionError


class TestCLIExecutor:
    """Test CLI executor functionality."""
    
    def test_execute_success(self):
        """Test successful command execution."""
        executor = CLIExecutor()
        stdout_lines = []
        stderr_lines = []
        
        def stdout_callback(line):
            stdout_lines.append(line)
        
        def stderr_callback(line):
            stderr_lines.append(line)
        
        # Use echo command (works on Unix and Windows)
        import sys
        if sys.platform == 'win32':
            command = ['cmd', '/c', 'echo', 'test output']
        else:
            command = ['echo', 'test output']
        
        exit_code, stdout, stderr = executor.execute(
            command,
            output_callback=stdout_callback,
            error_callback=stderr_callback
        )
        
        assert exit_code == 0
        assert len(stdout) > 0
        assert 'test output' in stdout[0] or 'test output' in ''.join(stdout)
    
    def test_execute_command_not_found(self):
        """Test error when command is not found."""
        executor = CLIExecutor()
        
        with pytest.raises(CLIExecutionError, match="Command not found"):
            executor.execute(['nonexistent_command_xyz123'])
    
    def test_execute_captures_exit_code(self):
        """Test that exit codes are captured correctly."""
        executor = CLIExecutor()
        
        import sys
        if sys.platform == 'win32':
            # On Windows, use a command that fails
            command = ['cmd', '/c', 'exit', '1']
        else:
            command = ['sh', '-c', 'exit 1']
        
        exit_code, stdout, stderr = executor.execute(command)
        
        assert exit_code == 1
    
    def test_check_command_exists_true(self):
        """Test check_command_exists returns True for existing command."""
        executor = CLIExecutor()
        
        import sys
        if sys.platform == 'win32':
            command = 'cmd'
        else:
            command = 'echo'
        
        assert executor.check_command_exists(command) is True
    
    def test_check_command_exists_false(self):
        """Test check_command_exists returns False for non-existent command."""
        executor = CLIExecutor()
        
        assert executor.check_command_exists('nonexistent_command_xyz123') is False
    
    def test_execute_with_working_directory(self):
        """Test execution with custom working directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = CLIExecutor()
            working_dir = Path(tmpdir)
            
            import sys
            if sys.platform == 'win32':
                command = ['cmd', '/c', 'cd']
            else:
                command = ['pwd']
            
            exit_code, stdout, stderr = executor.execute(
                command,
                working_directory=working_dir
            )
            
            assert exit_code == 0

