from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_user_management  # Fixed import
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreateByAdmin, UserResponse, UserUpdate, 
    UserWithCredentialsResponse, UserListResponse,
    PasswordStrengthResponse
)
from app.services.user_service import UserService
from app.utils.password_generator import PasswordGenerator


router = APIRouter()

@router.get("/", response_model=UserListResponse)
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Get all users (Admin and Super Admin only)
    """
    user_service = UserService(db)
    
    users = user_service.get_all_users(skip=skip, limit=limit)
    total = user_service.get_users_count()
    
    return UserListResponse(
        users=users,
        total=total,
        page=skip // limit + 1,
        page_size=limit
    )

@router.post("/", response_model=UserWithCredentialsResponse)
async def create_user_by_admin(
    user_data: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Create new user (Admin and Super Admin only)
    - Generates secure password if not provided
    - Returns credentials for the new user
    """
    user_service = UserService(db)
    
    try:
        result = user_service.create_user_by_admin(user_data, current_user)
        
        return UserWithCredentialsResponse(
            **result["user"].__dict__,
            generated_password=result["generated_password"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: UUID,
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Update user (Admin and Super Admin only)
    """
    user_service = UserService(db)
    
    try:
        user = user_service.update_user(user_id, update_data, current_user)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Deactivate user account (soft delete)
    """
    user_service = UserService(db)
    
    try:
        success = user_service.deactivate_user(user_id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {"message": "User deactivated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Activate user account
    """
    user_service = UserService(db)
    
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
    from app.core.permissions import PermissionService
    if not PermissionService.can_manage_users(current_user, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    user.is_active = True
    db.commit()
    
    return {"message": "User activated successfully"}

@router.delete("/{user_id}")
async def delete_user_permanently(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Permanently delete user (Super Admin only)
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can permanently delete users"
        )
    
    user_service = UserService(db)
    
    try:
        success = user_service.delete_user(user_id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {"message": "User deleted permanently"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user_management())
):
    """
    Reset user password (generates new secure password)
    """
    user_service = UserService(db)
    
    try:
        result = user_service.reset_password(user_id, current_user)
        return {
            "message": "Password reset successfully",
            "new_password": result["new_password"],
            "strength": result["strength"]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/tools/generate-password", response_model=PasswordStrengthResponse)
async def generate_secure_password():
    """
    Generate a secure random password with strength analysis
    """
    credentials = PasswordGenerator.generate_user_credentials()
    
    # Generate suggestions based on strength
    suggestions = []
    strength = credentials["strength"]
    
    if not strength["length"]:
        suggestions.append("Use at least 8 characters")
    if not strength["uppercase"]:
        suggestions.append("Include uppercase letters")
    if not strength["lowercase"]:
        suggestions.append("Include lowercase letters")
    if not strength["digit"]:
        suggestions.append("Include numbers")
    if not strength["special"]:
        suggestions.append("Include special characters")
    
    return PasswordStrengthResponse(
        strength=strength,
        suggestions=suggestions
    )