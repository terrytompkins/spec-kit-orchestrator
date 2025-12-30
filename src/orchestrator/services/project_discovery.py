"""Project discovery service for scanning workspace directories."""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models.project import Project
from ..services.config_manager import ConfigManager


class ProjectDiscovery:
    """Discovers Spec Kit projects in workspace directory."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize project discovery.
        
        Args:
            config_manager: Optional config manager. Creates new one if not provided.
        """
        if config_manager is None:
            config_manager = ConfigManager()
        self.config_manager = config_manager
        self.base_directory = config_manager.get_base_directory()
    
    def discover_projects(self) -> List[Project]:
        """
        Scan workspace directory for Spec Kit projects.
        
        A project is identified by the presence of a `.specify/` directory.
        
        Returns:
            List of discovered Project objects
        """
        projects = []
        
        if not self.base_directory.exists():
            return projects
        
        # Scan for directories containing .specify/
        for item in self.base_directory.iterdir():
            if not item.is_dir():
                continue
            
            specify_dir = item / '.specify'
            if specify_dir.exists() and specify_dir.is_dir():
                # Found a project
                try:
                    # Get last modified time
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    
                    project = Project(
                        name=item.name,
                        path=item,
                        init_timestamp=mtime,  # Use directory mtime as proxy
                        current_phase_status={},
                        artifacts=[],
                        executions=[]
                    )
                    projects.append(project)
                except (OSError, ValueError):
                    # Skip if we can't read directory info
                    continue
        
        return projects
    
    def get_project_state(self, project_path: Path) -> dict:
        """
        Get current state of a project (which phases run, artifact status).
        
        Args:
            project_path: Path to project
        
        Returns:
            Dictionary with project state information
        """
        state = {
            'phases_run': [],
            'artifacts': [],
            'last_execution': None
        }
        
        # Check for artifacts
        artifact_paths = {
            'constitution': project_path / '.specify' / 'memory' / 'constitution.md',
            'spec': None,  # Will check specs/ directory
            'plan': None,
            'tasks': None
        }
        
        # Check constitution
        if artifact_paths['constitution'].exists():
            state['artifacts'].append('constitution')
        
        # Check specs directory
        specs_dir = project_path / 'specs'
        if specs_dir.exists():
            for spec_dir in specs_dir.iterdir():
                if spec_dir.is_dir():
                    if (spec_dir / 'spec.md').exists():
                        state['artifacts'].append('spec')
                    if (spec_dir / 'plan.md').exists():
                        state['artifacts'].append('plan')
                    if (spec_dir / 'tasks.md').exists():
                        state['artifacts'].append('tasks')
        
        # Check execution history
        runs_dir = project_path / '.specify' / 'orchestrator' / 'runs'
        if runs_dir.exists():
            runs = sorted(runs_dir.iterdir(), reverse=True)
            if runs:
                state['last_execution'] = runs[0].name
        
        return state

