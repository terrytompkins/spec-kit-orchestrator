"""Artifact entity model."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .phase_execution import PhaseExecution


@dataclass
class Artifact:
    """Represents a generated Spec Kit artifact file."""
    
    artifact_type: str  # constitution, spec, clarification, plan, tasks, analysis
    file_path: Path
    generation_timestamp: datetime
    associated_execution: Optional[PhaseExecution]
    content_hash: str  # For staleness detection
    
    def __post_init__(self):
        """Ensure path is a Path object."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
    
    def exists(self) -> bool:
        """Check if artifact file exists."""
        return self.file_path.exists()
    
    def get_content(self) -> Optional[str]:
        """
        Read artifact content.
        
        Returns:
            File content as string, or None if file doesn't exist
        """
        if not self.exists():
            return None
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return None

