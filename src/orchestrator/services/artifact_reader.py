"""Artifact reader service for discovering and reading Spec Kit artifacts."""

from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from ..models.artifact import Artifact
from ..models.phase_execution import PhaseExecution


class ArtifactReader:
    """Reads and discovers Spec Kit artifacts."""
    
    # Known artifact locations
    ARTIFACT_PATTERNS = {
        'constitution': ['.specify/memory/constitution.md'],
        'spec': ['specs/*/spec.md'],
        'clarification': ['specs/*/clarifications.md'],
        'plan': ['specs/*/plan.md'],
        'tasks': ['specs/*/tasks.md'],
        'analysis': ['specs/*/analysis.md']
    }
    
    def __init__(self, project_path: Path):
        """
        Initialize artifact reader.
        
        Args:
            project_path: Path to Spec Kit project
        """
        self.project_path = project_path
    
    def discover_artifacts(self) -> List[Artifact]:
        """
        Discover all artifacts in the project.
        
        Returns:
            List of Artifact objects
        """
        artifacts = []
        
        # Check constitution
        constitution_path = self.project_path / '.specify' / 'memory' / 'constitution.md'
        if constitution_path.exists():
            artifacts.append(Artifact(
                artifact_type='constitution',
                file_path=constitution_path,
                generation_timestamp=datetime.fromtimestamp(constitution_path.stat().st_mtime),
                associated_execution=None,
                content_hash=''  # Could calculate if needed
            ))
        
        # Check specs directory
        specs_dir = self.project_path / 'specs'
        if specs_dir.exists():
            for spec_dir in specs_dir.iterdir():
                if not spec_dir.is_dir():
                    continue
                
                # Check for spec.md
                spec_path = spec_dir / 'spec.md'
                if spec_path.exists():
                    artifacts.append(Artifact(
                        artifact_type='spec',
                        file_path=spec_path,
                        generation_timestamp=datetime.fromtimestamp(spec_path.stat().st_mtime),
                        associated_execution=None,
                        content_hash=''
                    ))
                
                # Check for plan.md
                plan_path = spec_dir / 'plan.md'
                if plan_path.exists():
                    artifacts.append(Artifact(
                        artifact_type='plan',
                        file_path=plan_path,
                        generation_timestamp=datetime.fromtimestamp(plan_path.stat().st_mtime),
                        associated_execution=None,
                        content_hash=''
                    ))
                
                # Check for tasks.md
                tasks_path = spec_dir / 'tasks.md'
                if tasks_path.exists():
                    artifacts.append(Artifact(
                        artifact_type='tasks',
                        file_path=tasks_path,
                        generation_timestamp=datetime.fromtimestamp(tasks_path.stat().st_mtime),
                        associated_execution=None,
                        content_hash=''
                    ))
                
                # Check for clarifications.md
                clar_path = spec_dir / 'clarifications.md'
                if clar_path.exists():
                    artifacts.append(Artifact(
                        artifact_type='clarification',
                        file_path=clar_path,
                        generation_timestamp=datetime.fromtimestamp(clar_path.stat().st_mtime),
                        associated_execution=None,
                        content_hash=''
                    ))
                
                # Check for analysis.md
                analysis_path = spec_dir / 'analysis.md'
                if analysis_path.exists():
                    artifacts.append(Artifact(
                        artifact_type='analysis',
                        file_path=analysis_path,
                        generation_timestamp=datetime.fromtimestamp(analysis_path.stat().st_mtime),
                        associated_execution=None,
                        content_hash=''
                    ))
        
        return artifacts
    
    def read_artifact(self, artifact_type: str) -> Optional[Artifact]:
        """
        Read a specific artifact by type.
        
        Args:
            artifact_type: Type of artifact to read
        
        Returns:
            Artifact object or None if not found
        """
        artifacts = self.discover_artifacts()
        for artifact in artifacts:
            if artifact.artifact_type == artifact_type:
                return artifact
        return None
    
    def read_execution_log(self, run_dir: Path, log_type: str = 'stdout') -> Optional[str]:
        """
        Read execution log from a run directory.
        
        Args:
            run_dir: Path to run directory
            log_type: 'stdout' or 'stderr'
        
        Returns:
            Log content or None if not found
        """
        log_file = run_dir / f'{log_type}.log'
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return None
        return None
    
    def get_related_artifacts(self, artifact_type: str) -> Dict[str, Optional[Artifact]]:
        """
        Get artifacts related to a given artifact type.
        
        For example, for 'spec', returns plan and tasks if they exist.
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            Dictionary mapping related artifact types to Artifact objects
        """
        artifacts = self.discover_artifacts()
        artifact_map = {a.artifact_type: a for a in artifacts}
        
        # Define relationships
        relationships = {
            'spec': ['plan', 'tasks'],
            'plan': ['spec', 'tasks'],
            'tasks': ['spec', 'plan']
        }
        
        related = {}
        if artifact_type in relationships:
            for related_type in relationships[artifact_type]:
                related[related_type] = artifact_map.get(related_type)
        
        return related

