from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create new dashboard user (Admin only)
    """
    user_service = UserService(db)
    
    try:
        user = user_service.create_user(user_data, created_by=current_user)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get all users (Admin only)
    """
    user_service = UserService(db)
    return user_service.get_all_users()

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update user (Admin only)
    """
    user_service = UserService(db)
    user = user_service.update_user(user_id, update_data)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    # ✅ Simply return the user - let Pydantic handle the serialization
    return current_user