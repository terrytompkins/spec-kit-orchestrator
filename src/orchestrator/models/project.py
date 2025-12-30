"""Project entity model."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .phase_execution import PhaseExecution
from .artifact import Artifact


@dataclass
class Project:
    """Represents a Spec Kit project instance."""
    
    name: str
    path: Path
    init_timestamp: datetime
    current_phase_status: Dict[str, str] = field(default_factory=dict)  # phase -> status
    artifacts: List[Artifact] = field(default_factory=list)
    executions: List[PhaseExecution] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure path is a Path object."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
    
    def get_phase_status(self, phase_name: str) -> str:
        """
        Get status of a specific phase.
        
        Args:
            phase_name: Name of the phase
        
        Returns:
            Status string (not_started, in_progress, completed, failed)
        """
        return self.current_phase_status.get(phase_name, "not_started")
    
    def update_phase_status(self, phase_name: str, status: str) -> None:
        """
        Update status of a phase.
        
        Args:
            phase_name: Name of the phase
            status: New status
        """
        self.current_phase_status[phase_name] = status
    
    def has_artifact(self, artifact_type: str) -> bool:
        """
        Check if project has a specific artifact type.
        
        Args:
            artifact_type: Type of artifact (constitution, spec, etc.)
        
        Returns:
            True if artifact exists, False otherwise
        """
        return any(artifact.artifact_type == artifact_type for artifact in self.artifacts)
    
    def get_latest_execution(self, phase_name: Optional[str] = None) -> Optional[PhaseExecution]:
        """
        Get the most recent execution, optionally filtered by phase.
        
        Args:
            phase_name: Optional phase name to filter by
        
        Returns:
            Most recent PhaseExecution or None
        """
        filtered = self.executions
        if phase_name:
            filtered = [e for e in self.executions if e.phase_name == phase_name]
        
        if not filtered:
            return None
        
        return max(filtered, key=lambda e: e.start_timestamp)

