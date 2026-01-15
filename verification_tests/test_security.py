import pytest
import os
from pathlib import Path
from fastapi import HTTPException
from app.core.security_utils import validate_safe_path

def test_validate_safe_path_valid():
    # Setup: Create a temporary file
    base_dir = os.getcwd()
    test_file_name = "test_safe.txt"
    test_file = Path(base_dir) / test_file_name
    test_file.touch()
    
    try:
        # Test absolute path
        result = validate_safe_path(base_dir, str(test_file))
        assert result == str(test_file)
        
        # Test relative path
        result = validate_safe_path(base_dir, test_file_name)
        assert result == str(test_file)
    finally:
        if test_file.exists():
            test_file.unlink()

def test_validate_safe_path_traversal():
    # Create a jailed directory
    base_dir = os.path.join(os.getcwd(), "test_jail")
    os.makedirs(base_dir, exist_ok=True)
    
    # Create a file OUTSIDE the jail
    outside_file = Path(os.getcwd()) / "outside.txt"
    outside_file.touch()
    
    try:
        # Attempt to access file outside base_dir using ..
        # Note: on Windows/Linux ../ interpretation might vary if not fully resolved, but our util resolves it.
        # "test_jail/../outside.txt" -> "cwd/outside.txt"
        
        with pytest.raises(HTTPException) as excinfo:
            validate_safe_path(base_dir, "../outside.txt")
        assert excinfo.value.status_code == 403
        
        # Attempt to access using absolute path of outside file
        with pytest.raises(HTTPException) as excinfo:
            validate_safe_path(base_dir, str(outside_file))
        assert excinfo.value.status_code == 403

    finally:
        if outside_file.exists():
            outside_file.unlink()
        os.rmdir(base_dir)

def test_validate_safe_path_not_found():
    base_dir = os.getcwd()
    with pytest.raises(HTTPException) as excinfo:
        validate_safe_path(base_dir, "non_existent_file.txt")
    assert excinfo.value.status_code == 404
