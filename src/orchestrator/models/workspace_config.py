"""Workspace configuration entity model."""

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class WorkspaceConfiguration:
    """Represents administrator-configured settings."""
    
    base_directory: Path
    allowed_ai_agent_values: List[str]
    secrets_storage: str  # "environment" or "secure_store"
    mask_secrets_in_logs: bool
    
    def __post_init__(self):
        """Ensure path is a Path object."""
        if isinstance(self.base_directory, str):
            self.base_directory = Path(self.base_directory)
    
    def is_ai_agent_allowed(self, agent: str) -> bool:
        """
        Check if an AI agent value is allowed.
        
        Args:
            agent: AI agent name to check
        
        Returns:
            True if allowed, False otherwise
        """
        return agent in self.allowed_ai_agent_values

