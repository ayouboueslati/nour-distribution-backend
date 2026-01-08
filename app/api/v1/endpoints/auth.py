from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.schemas.user import Token, LoginRequest
from app.services.user_service import UserService
from app.models.user import User
from app.api.v1.deps import get_current_user
router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    """
    user_service = UserService(db)
    user = user_service.authenticate_user(login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )
    
    # ✅ FIX: Pass user object to include role in token
    access_token = create_access_token(data={"user": user})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60  # 30 minutes in seconds
    }

@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh access token (implementation for refresh tokens)
    """
    new_access_token = create_access_token(data={"sub": current_user.email})
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60
    }