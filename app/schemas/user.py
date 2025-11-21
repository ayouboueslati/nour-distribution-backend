from pydantic import BaseModel, EmailStr, validator, field_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.STAFF


class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserCreateByAdmin(UserBase):
    """Schema for admin creating users - password is optional (generated if not provided)"""
    password: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserProfileUpdate(BaseModel):
    """Schema for users updating their own profile"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('New password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('New password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('New password must contain at least one digit')
        return v


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    created_by: Optional[UUID] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
    )


class UserWithCredentialsResponse(UserResponse):
    """Response with generated credentials (for admin use only)"""
    generated_password: Optional[str] = None


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    page_size: int


class PasswordStrengthResponse(BaseModel):
    strength: Dict[str, bool]
    suggestions: list[str]


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str