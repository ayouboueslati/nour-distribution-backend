import os
from pathlib import Path
from fastapi import HTTPException, status

def validate_safe_path(base_dir: str, requested_path: str) -> str:
    """
    Validate that a requested path is within the base directory to prevent path traversal.
    
    Args:
        base_dir: The base directory that acts as the jail.
        requested_path: The full path or relative path requested.
        
    Returns:
        The absolute path if it is safe and exists.
        
    Raises:
        HTTPException(400) if the path attempts traversal out of base_dir.
        HTTPException(404) if the file doesn't exist (optional, but good for security to not leak existence separate from access).
    """
    # Resolve the base directory to its absolute path
    base_path = Path(base_dir).resolve()
    
    # Resolve the requested path to its absolute path
    # If requested_path is absolute, Path(requested_path) works.
    # If relative, it will be relative to CWD, which might not be what we want if we expect it relative to base_dir.
    # The current usage in client_portal is `document.pdf_path` which likely stores a relative path "documents/..." 
    # or absolute. 
    # Let's assume the input `requested_path` is the full path we want to check, OR a relative path that we join with CWD.
    # However, usually we want to ensure `requested_path` is inside `base_dir`.
    
    # In the context of the identified issue, `document.pdf_path` is passed.
    # We should normalize it.
    
    target_path = Path(requested_path).resolve()
    
    # Check if the target path is strictly within the base path
    # usage of os.path.commonpath or pathlib's .is_relative_to (Python 3.9+)
    
    # For compatibility and robustness:
    try:
        target_path.relative_to(base_path)
    except ValueError:
        # If it's not relative to base_path, it's outside
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid file path"
        )
        
    if not target_path.exists() or not target_path.is_file():
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return str(target_path)
