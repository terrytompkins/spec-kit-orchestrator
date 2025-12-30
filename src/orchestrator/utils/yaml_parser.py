"""YAML parsing and generation utilities."""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """
    Load YAML file and return as dictionary.
    
    Args:
        file_path: Path to YAML file
    
    Returns:
        Dictionary containing YAML content
    
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def save_yaml(data: Dict[str, Any], file_path: Path) -> None:
    """
    Save dictionary to YAML file.
    
    Args:
        data: Dictionary to save
        file_path: Path to YAML file
    
    Raises:
        OSError: If file cannot be written
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def validate_yaml_structure(data: Dict[str, Any], required_keys: Optional[List[str]] = None) -> bool:
    """
    Validate YAML structure has required keys.
    
    Args:
        data: Dictionary to validate
        required_keys: List of required top-level keys
    
    Returns:
        True if valid, False otherwise
    """
    if required_keys is None:
        return True
    
    return all(key in data for key in required_keys)

