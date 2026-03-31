"""Parameter document generator service."""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..utils.yaml_parser import save_yaml


class ParameterGenerator:
    """Generates Spec Kit command parameter documents."""
    
    PHASES = ['constitution', 'specify', 'clarify', 'plan', 'tasks', 'analyze']
    
    def __init__(self, project_path: Path):
        """
        Initialize parameter generator.
        
        Args:
            project_path: Path to Spec Kit project
        """
        self.project_path = project_path
        self.docs_dir = project_path / 'docs'
        self.docs_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create a timestamped backup of an existing file.
        
        Args:
            file_path: Path to file to backup
        
        Returns:
            Path to backup file, or None if original doesn't exist
        """
        if not file_path.exists():
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        backup_path = file_path.parent / f"{file_path.stem}.{timestamp}{file_path.suffix}"
        
        # Copy file
        import shutil
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    
    def generate_markdown(self, parameters: Dict[str, Dict[str, Any]]) -> str:
        """
        Generate Markdown format parameter document.
        
        Args:
            parameters: Dictionary mapping phase names to parameter dictionaries
        
        Returns:
            Markdown content
        """
        lines = ["# Spec Kit Command Parameters (Copy/Paste)", ""]
        lines.append("This document contains copy/paste parameter blocks for each Spec Kit phase.")
        lines.append("Paste each block (or the content inside it) into your IDE **after** the corresponding slash command (e.g. `/speckit.constitution`).")
        lines.append("")
        
        for phase in self.PHASES:
            if phase not in parameters:
                continue
            
            phase_params = parameters[phase]
            lines.append(f"## {phase.title()} Phase")
            lines.append("")
            lines.append("```text")
            lines.append(f"Command: {phase_params.get('command', f'speckit.{phase}')}")
            lines.append("")
            
            # Format parameters
            for key, value in phase_params.get('parameters', {}).items():
                if isinstance(value, str) and '\n' in value:
                    lines.append(f"{key}:")
                    for line in value.split('\n'):
                        lines.append(f"  {line}")
                else:
                    lines.append(f"{key}: {value}")
            
            lines.append("```")
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_yaml(self, parameters: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate YAML format parameter document.
        
        Args:
            parameters: Dictionary mapping phase names to parameter dictionaries
        
        Returns:
            YAML structure as dictionary
        """
        yaml_data = {
            'phases': {}
        }
        
        for phase in self.PHASES:
            if phase not in parameters:
                continue
            
            phase_params = parameters[phase]
            yaml_data['phases'][phase] = {
                'command': phase_params.get('command', f'speckit.{phase}'),
                'parameters': phase_params.get('parameters', {})
            }
        
        return yaml_data
    
    def save_parameter_documents(
        self,
        parameters: Dict[str, Dict[str, Any]],
        create_backups: bool = True
    ):
        """
        Save parameter documents in both Markdown and YAML formats.
        
        Args:
            parameters: Dictionary mapping phase names to parameter dictionaries
            create_backups: Whether to create backups of existing files
        
        Returns:
            Tuple of (markdown_path, yaml_path)
        """
        markdown_path = self.docs_dir / 'spec-kit-parameters.md'
        yaml_path = self.docs_dir / 'spec-kit-parameters.yml'
        
        # Create backups if requested
        backup_md = None
        backup_yml = None
        if create_backups:
            backup_md = self.create_backup(markdown_path)
            backup_yml = self.create_backup(yaml_path)
        
        # Generate and save Markdown
        markdown_content = self.generate_markdown(parameters)
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Generate and save YAML
        yaml_data = self.generate_yaml(parameters)
        save_yaml(yaml_data, yaml_path)
        
        return markdown_path, yaml_path, backup_md, backup_yml
    
    def validate_parameters(self, parameters: Dict[str, Dict[str, Any]]) -> tuple[bool, List[str]]:
        """
        Validate that parameters contain all required phases.
        
        Args:
            parameters: Dictionary mapping phase names to parameter dictionaries
        
        Returns:
            Tuple of (is_valid, list_of_missing_phases)
        """
        missing = []
        for phase in self.PHASES:
            if phase not in parameters:
                missing.append(phase)
        
        return len(missing) == 0, missing

