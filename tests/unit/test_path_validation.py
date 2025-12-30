"""Unit tests for path validation utilities."""

import pytest
from pathlib import Path
import tempfile
import os

from src.orchestrator.utils.path_validation import (
    validate_path,
    is_within_base,
    PathValidationError
)


class TestPathValidation:
    """Test path validation functions."""
    
    def test_valid_path_within_base(self):
        """Test that valid paths within base directory are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            user_path = "subdir/project"
            
            result = validate_path(user_path, base)
            assert result == (base / user_path).resolve()
    
    def test_directory_traversal_prevention(self):
        """Test that directory traversal attempts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            
            with pytest.raises(PathValidationError, match="directory traversal"):
                validate_path("../../../etc/passwd", base)
    
    def test_path_outside_base_rejected(self):
        """Test that paths outside base directory are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                base = Path(tmpdir1)
                outside_path = Path(tmpdir2) / "project"
                
                with pytest.raises(PathValidationError, match="outside allowed"):
                    validate_path(str(outside_path), base)
    
    def test_absolute_path_within_base(self):
        """Test that absolute paths within base are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            project_dir = base / "project"
            project_dir.mkdir()
            
            result = validate_path(str(project_dir), base)
            assert result == project_dir.resolve()
    
    def test_is_within_base_true(self):
        """Test is_within_base returns True for paths within base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = base / "subdir" / "file.txt"
            
            assert is_within_base(path, base) is True
    
    def test_is_within_base_false(self):
        """Test is_within_base returns False for paths outside base."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                base = Path(tmpdir1)
                path = Path(tmpdir2) / "file.txt"
                
                assert is_within_base(path, base) is False

