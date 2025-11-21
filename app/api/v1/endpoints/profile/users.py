from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserProfileUpdate, UserPasswordUpdate
from app.services.user_service import UserService

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile (email, full name)
    """
    user_service = UserService(db)
    
    user = user_service.update_user_profile(current_user.id, profile_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.post("/me/change-password")
async def change_current_user_password(
    password_data: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change current user password
    """
    user_service = UserService(db)
    
    try:
        success = user_service.change_password(current_user.id, password_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me/stats")
async def get_current_user_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user statistics and activity
    """
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
        "created_at": current_user.created_at,
        "failed_login_attempts": current_user.failed_login_attempts,
        "is_locked": current_user.is_locked,
        "password_changed_at": current_user.password_changed_at
    }