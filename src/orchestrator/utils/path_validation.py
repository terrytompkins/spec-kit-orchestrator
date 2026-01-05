"""Path validation utilities for preventing directory traversal attacks."""

from pathlib import Path
from typing import Optional
import os


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def normalize_macos_path(path: Path) -> Path:
    """
    Normalize paths to avoid macOS system volume issues.
    
    On macOS, Path.resolve() can resolve /Users/... to /System/Volumes/Data/home/...
    which is a read-only system volume. This function converts such paths back to
    their canonical /Users/... form.
    
    On Linux and other platforms, this function is a no-op and returns the path
    unchanged, making it safe to use cross-platform.
    
    Args:
        path: Path to normalize
        
    Returns:
        Normalized Path with macOS system volume paths converted to /Users/...
        On non-macOS systems, returns the path unchanged.
    """
    path_str = str(path)
    
    # Check if path is in the system volume
    if path_str.startswith('/System/Volumes/Data/home/'):
        # Convert /System/Volumes/Data/home/username to /Users/username
        remaining = path_str[len('/System/Volumes/Data/home/'):]
        # Extract username (first component)
        parts = remaining.split('/', 1)
        if parts:
            username = parts[0]
            rest = parts[1] if len(parts) > 1 else ''
            normalized = f'/Users/{username}'
            if rest:
                normalized = f'{normalized}/{rest}'
            return Path(normalized)
    
    return path


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
    # Ensure base directory is absolute and normalize macOS paths
    base_resolved = normalize_macos_path(base_directory.resolve())
    
    # Check for obvious directory traversal attempts
    if '..' in user_path:
        raise PathValidationError(
            f"Path contains directory traversal attempt: {user_path}"
        )
    
    # Resolve the user path
    try:
        if Path(user_path).is_absolute():
            resolved = normalize_macos_path(Path(user_path).resolve())
        else:
            # If relative, resolve against base directory
            resolved = normalize_macos_path((base_resolved / user_path).resolve())
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
        normalized_path = normalize_macos_path(path.resolve())
        normalized_base = normalize_macos_path(base_directory.resolve())
        normalized_path.relative_to(normalized_base)
        return True
    except ValueError:
        return False

