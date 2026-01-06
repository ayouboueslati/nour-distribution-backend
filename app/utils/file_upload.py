import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from pathlib import Path

# Define upload directory
UPLOAD_DIR = Path("static/products")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def ensure_upload_directory():
    """Ensure the upload directory exists"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

async def save_upload_file(file: UploadFile, subfolder: str = "") -> str:
    """
    Save an uploaded file and return its path
    
    Args:
        file: The uploaded file
        subfolder: Optional subfolder within the upload directory
        
    Returns:
        The relative path to the saved file (e.g., "products/abc-123.jpg")
    """
    # Validate file
    validate_image_file(file)
    
    # Ensure directory exists
    ensure_upload_directory()
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Create full path
    if subfolder:
        save_dir = UPLOAD_DIR / subfolder
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / unique_filename
    else:
        file_path = UPLOAD_DIR / unique_filename
    
    # Read and save file
    try:
        contents = await file.read()
        
        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        with open(file_path, "wb") as f:
            f.write(contents)
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )
    finally:
        await file.seek(0)  # Reset file pointer
    
    # Return relative path for database storage
    if subfolder:
        return f"products/{subfolder}/{unique_filename}"
    return f"products/{unique_filename}"

def delete_file(file_path: str) -> bool:
    """
    Delete a file from the static directory
    
    Args:
        file_path: Relative path to the file (e.g., "products/abc-123.jpg")
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        full_path = Path("static") / file_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    except Exception:
        return False
