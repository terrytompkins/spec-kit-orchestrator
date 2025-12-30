"""Path validation utilities for preventing directory traversal attacks."""

from pathlib import Path
from typing import Optional


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def validate_path(user_path: str, base_directory: Path) -> Path:
    """
    Validate and resolve a user-provided path against a base directory.
    
    Prevents directory traversal attacks by ensuring the resolved path
    is within the allowed base directory.
    
    Args:
        user_path: User-provided path (can be relative or absolute)
        base_directory: Admin-configured base directory (must be absolute)
    
    Returns:
        Resolved absolute Path that is within base_directory
    
    Raises:
        PathValidationError: If path is outside base directory or contains traversal attempts
    """
    # Ensure base directory is absolute
    base_resolved = base_directory.resolve()
    
    # Check for obvious directory traversal attempts
    if '..' in user_path:
        raise PathValidationError(
            f"Path contains directory traversal attempt: {user_path}"
        )
    
    # Resolve the user path
    try:
        if Path(user_path).is_absolute():
            resolved = Path(user_path).resolve()
        else:
            # If relative, resolve against base directory
            resolved = (base_resolved / user_path).resolve()
    except (OSError, ValueError) as e:
        raise PathValidationError(f"Invalid path: {user_path} - {str(e)}")
    
    # Verify resolved path is within base directory
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise PathValidationError(
            f"Path outside allowed base directory: {resolved} (base: {base_resolved})"
        )
    
    return resolved


def is_within_base(path: Path, base_directory: Path) -> bool:
    """
    Check if a path is within the base directory.
    
    Args:
        path: Path to check
        base_directory: Base directory
    
    Returns:
        True if path is within base directory, False otherwise
    """
    try:
        path.resolve().relative_to(base_directory.resolve())
        return True
    except ValueError:
        return False

