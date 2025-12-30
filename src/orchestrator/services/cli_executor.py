"""CLI execution wrapper with streaming output."""

import subprocess
import shlex
from pathlib import Path
from typing import List, Optional, Callable, Tuple
import threading
import queue


class CLIExecutionError(Exception):
    """Raised when CLI execution fails."""
    pass


class CLIExecutor:
    """Executes CLI commands with real-time output streaming."""
    
    def __init__(self, working_directory: Optional[Path] = None):
        """
        Initialize CLI executor.
        
        Args:
            working_directory: Default working directory for commands
        """
        self.working_directory = working_directory
    
    def execute(
        self,
        command: List[str],
        working_directory: Optional[Path] = None,
        env: Optional[dict] = None,
        output_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[int, List[str], List[str]]:
        """
        Execute a command and stream output in real-time.
        
        Args:
            command: Command and arguments as list (e.g., ['specify', 'init', '--ai', 'claude'])
            working_directory: Working directory for command (overrides default)
            env: Environment variables (merged with current env)
            output_callback: Optional callback for each stdout line
            error_callback: Optional callback for each stderr line
        
        Returns:
            Tuple of (exit_code, stdout_lines, stderr_lines)
        """
        cwd = working_directory or self.working_directory
        
        # Prepare environment
        process_env = None
        if env:
            import os
            process_env = os.environ.copy()
            process_env.update(env)
        
        # Start process
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                cwd=str(cwd) if cwd else None,
                env=process_env
            )
        except FileNotFoundError as e:
            raise CLIExecutionError(f"Command not found: {command[0]}") from e
        except Exception as e:
            raise CLIExecutionError(f"Failed to start command: {str(e)}") from e
        
        # Collect output
        stdout_lines = []
        stderr_lines = []
        
        # Read stdout
        def read_stdout():
            for line in iter(process.stdout.readline, ''):
                line = line.rstrip('\n\r')
                stdout_lines.append(line)
                if output_callback:
                    output_callback(line)
            process.stdout.close()
        
        # Read stderr
        def read_stderr():
            for line in iter(process.stderr.readline, ''):
                line = line.rstrip('\n\r')
                stderr_lines.append(line)
                if error_callback:
                    error_callback(line)
            process.stderr.close()
        
        # Start reading threads
        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process to complete
        exit_code = process.wait()
        
        # Wait for output threads to finish
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)
        
        return exit_code, stdout_lines, stderr_lines
    
    def check_command_exists(self, command: str) -> bool:
        """
        Check if a command exists in PATH.
        
        Args:
            command: Command name to check
        
        Returns:
            True if command exists, False otherwise
        """
        try:
            result = subprocess.run(
                ['which', command] if Path('/usr/bin/which').exists() else ['where', command],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Try alternative method
            try:
                subprocess.run(
                    [command, '--version'],
                    capture_output=True,
                    timeout=2
                )
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False

