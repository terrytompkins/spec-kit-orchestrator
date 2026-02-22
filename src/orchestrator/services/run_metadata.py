"""Create and manage execution metadata JSON files."""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import os

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class RunMetadata:
    """Manages execution metadata for Spec Kit phase runs."""
    
    def __init__(self, project_path: Path):
        """
        Initialize run metadata manager.
        
        Args:
            project_path: Path to the Spec Kit project
        """
        self.project_path = project_path
        self.runs_dir = project_path / '.specify' / 'orchestrator' / 'runs'
        self.runs_dir.mkdir(parents=True, exist_ok=True)
    
    def create_run_directory(self) -> Path:
        """
        Create a timestamped directory for a new run.
        
        Returns:
            Path to the run directory
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        run_dir = self.runs_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir
    
    def get_git_commit_hash(self) -> Optional[str]:
        """
        Get current git commit hash if project is a git repository.
        
        Returns:
            Git commit hash or None if not a git repo
        """
        if not GIT_AVAILABLE:
            return None
        
        try:
            repo = git.Repo(self.project_path, search_parent_directories=True)
            return repo.head.commit.hexsha
        except (git.InvalidGitRepositoryError, git.GitCommandError):
            return None
    
    def calculate_inputs_hash(self, command: str, args: List[str], env_vars: Dict[str, str]) -> str:
        """
        Calculate SHA256 hash of inputs for staleness detection.
        
        Args:
            command: Command executed
            args: Command arguments
            env_vars: Environment variables (non-secret)
        
        Returns:
            SHA256 hash as hex string
        """
        # Create a deterministic string representation
        inputs_str = json.dumps({
            'command': command,
            'args': sorted(args),  # Sort for determinism
            'env': sorted(env_vars.items())  # Sort for determinism
        }, sort_keys=True)
        
        return hashlib.sha256(inputs_str.encode('utf-8')).hexdigest()
    
    def create_metadata(
        self,
        phase_name: str,
        command: str,
        args: List[str],
        working_directory: Path,
        environment_vars: Dict[str, str],
        start_timestamp: datetime,
        end_timestamp: Optional[datetime],
        exit_code: Optional[int],
        stdout_log_path: Path,
        stderr_log_path: Path,
        run_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Create execution metadata dictionary.
        
        Args:
            phase_name: Name of the phase (constitution, specify, etc.)
            command: Full command string
            args: Command arguments
            working_directory: Working directory when command executed
            environment_vars: Non-secret environment variables
            start_timestamp: When execution started
            end_timestamp: When execution completed (None if in progress)
            exit_code: Process exit code (None if in progress)
            stdout_log_path: Path to stdout log file
            stderr_log_path: Path to stderr log file
            run_dir: Run directory (created if not provided)
        
        Returns:
            Metadata dictionary
        """
        if run_dir is None:
            run_dir = self.create_run_directory()
        
        # Calculate inputs hash for staleness detection
        inputs_hash = self.calculate_inputs_hash(command, args, environment_vars)
        
        # Get git commit hash if available
        git_commit_hash = self.get_git_commit_hash()
        
        # Determine status
        if end_timestamp is None:
            status = "in_progress"
        elif exit_code == 0:
            status = "success"
        else:
            status = "failure"
        
        # Make log paths relative to project root
        project_root = self.project_path
        try:
            stdout_rel = stdout_log_path.relative_to(project_root)
            stderr_rel = stderr_log_path.relative_to(project_root)
        except ValueError:
            # If paths are outside project, use absolute
            stdout_rel = str(stdout_log_path)
            stderr_rel = str(stderr_log_path)
        
        metadata = {
            "phase_name": phase_name,
            "command": command,
            "args": args,
            "working_directory": str(working_directory),
            "environment_vars": environment_vars,
            "start_timestamp": start_timestamp.isoformat() + 'Z',
            "end_timestamp": end_timestamp.isoformat() + 'Z' if end_timestamp else None,
            "status": status,
            "exit_code": exit_code,
            "stdout_log_path": str(stdout_rel),
            "stderr_log_path": str(stderr_rel),
            "git_commit_hash": git_commit_hash,
            "inputs_hash": f"sha256:{inputs_hash}"
        }
        
        return metadata
    
    def save_metadata(self, metadata: Dict[str, Any], run_dir: Path) -> Path:
        """
        Save metadata to JSON file.
        
        Args:
            metadata: Metadata dictionary
            run_dir: Run directory
        
        Returns:
            Path to metadata file
        """
        metadata_file = run_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return metadata_file
    
    def load_metadata(self, run_dir: Path) -> Dict[str, Any]:
        """
        Load metadata from JSON file.
        
        Args:
            run_dir: Run directory
        
        Returns:
            Metadata dictionary
        """
        metadata_file = run_dir / 'metadata.json'
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_runs(self) -> List[Path]:
        """
        List all run directories, sorted by timestamp (newest first).
        
        Returns:
            List of run directory paths
        """
        if not self.runs_dir.exists():
            return []
        
        runs = [d for d in self.runs_dir.iterdir() if d.is_dir()]
        # Sort by directory name (timestamp format ensures chronological sort)
        runs.sort(reverse=True)
        return runs

