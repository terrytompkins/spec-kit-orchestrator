"""Phase execution entity model."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class PhaseExecution:
    """Represents a single run of a Spec Kit phase."""
    
    phase_name: str  # constitution, specify, clarify, plan, tasks, analyze
    command: str
    args: List[str]
    working_directory: Path
    start_timestamp: datetime
    end_timestamp: Optional[datetime]
    exit_code: Optional[int]
    status: str  # success, failure, in_progress
    stdout_log_path: Path
    stderr_log_path: Path
    git_commit_hash: Optional[str]
    inputs_hash: str  # SHA256 hash for staleness detection
    
    def __post_init__(self):
        """Ensure paths are Path objects."""
        if isinstance(self.working_directory, str):
            self.working_directory = Path(self.working_directory)
        if isinstance(self.stdout_log_path, str):
            self.stdout_log_path = Path(self.stdout_log_path)
        if isinstance(self.stderr_log_path, str):
            self.stderr_log_path = Path(self.stderr_log_path)
    
    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.status == "success" and self.exit_code == 0
    
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == "failure" or (self.exit_code is not None and self.exit_code != 0)
    
    def is_in_progress(self) -> bool:
        """Check if execution is in progress."""
        return self.status == "in_progress"

