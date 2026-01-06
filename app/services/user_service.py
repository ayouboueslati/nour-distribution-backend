from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserCreateByAdmin, UserProfileUpdate, UserPasswordUpdate
from app.core.security import get_password_hash, verify_password
from app.core.permissions import PermissionService  # This import is safe now
from app.utils.password_generator import PasswordGenerator
from datetime import datetime, timedelta, timezone
import uuid

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return self.db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_users_count(self) -> int:
        return self.db.query(User).count()
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with security checks"""
        user = self.get_user_by_email(email)
        
        if not user or not user.is_active:
            return None
        
        # Check if account is locked
        if user.is_locked:
            return None
        
        if not verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts for 30 minutes
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            self.db.commit()
            return None
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        
        return user
    
    def create_user(self, user_data: UserCreate, created_by: User = None) -> User:
        """Create new user"""
        # Check if email already exists
        if self.get_user_by_email(user_data.email):
            raise ValueError("Email already registered")
        
        hashed_password = get_password_hash(user_data.password)
        
        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
            created_by=created_by.id if created_by else None
        )
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise ValueError("User creation failed")
    
    def create_user_by_admin(self, user_data: UserCreateByAdmin, admin_user: User) -> Dict[str, Any]:
        """Create user by admin with optional password generation"""
        # Check permissions
        if not PermissionService.can_manage_users(admin_user):
            raise ValueError("Insufficient permissions to create user")
        
        if not PermissionService.can_change_role(admin_user, user_data.role):
            raise ValueError("Cannot assign this role")
        
        # Generate password if not provided
        password = user_data.password
        generated_password = None
        
        if not password:
            credentials = PasswordGenerator.generate_user_credentials()
            password = credentials["password"]
            generated_password = password
        
        # Create user data for standard creation
        create_data = UserCreate(
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            password=password
        )
        
        user = self.create_user(create_data, created_by=admin_user)
        
        return {
            "user": user,
            "generated_password": generated_password
        }
    
    def update_user(self, user_id: uuid.UUID, update_data: UserUpdate, updated_by: User = None) -> Optional[User]:
        """Update user details (admin function)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Check permissions if updated_by is provided
        if updated_by and not PermissionService.can_manage_users(updated_by, user):
            raise ValueError("Insufficient permissions to update this user")
        
        # Role change permission check
        if update_data.role and updated_by:
            if not PermissionService.can_change_role(updated_by, update_data.role):
                raise ValueError("Cannot assign this role")
        
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            if field == "password" and value:
                user.hashed_password = get_password_hash(value)
                user.password_changed_at = datetime.now(timezone.utc)
            else:
                setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user_profile(self, user_id: uuid.UUID, update_data: UserProfileUpdate) -> Optional[User]:
        """Update user's own profile (non-sensitive data)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def change_password(self, user_id: uuid.UUID, password_data: UserPasswordUpdate) -> bool:
        """Change user password with current password verification"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        
        # Update to new password
        user.hashed_password = get_password_hash(password_data.new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        
        self.db.commit()
        return True
    
    def deactivate_user(self, user_id: uuid.UUID, admin_user: User) -> bool:
        """Deactivate user (soft delete)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Check permissions
        if not PermissionService.can_manage_users(admin_user, user):
            raise ValueError("Insufficient permissions to deactivate this user")
        
        # Cannot deactivate yourself
        if user.id == admin_user.id:
            raise ValueError("Cannot deactivate your own account")
        
        user.is_active = False
        self.db.commit()
        return True
    
    def delete_user(self, user_id: uuid.UUID, admin_user: User) -> bool:
        """Permanently delete user (super admin only)"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Check permissions
        if not PermissionService.can_delete_user(admin_user, user):
            raise ValueError("Insufficient permissions to delete this user")
        
        # Cannot delete yourself
        if user.id == admin_user.id:
            raise ValueError("Cannot delete your own account")
        
        self.db.delete(user)
        self.db.commit()
        return True
    
    def reset_password(self, user_id: uuid.UUID, admin_user: User) -> Dict[str, str]:
        """Reset user password (admin function)"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Check permissions
        if not PermissionService.can_manage_users(admin_user, user):
            raise ValueError("Insufficient permissions to reset password for this user")
        
        # Generate new password
        credentials = PasswordGenerator.generate_user_credentials()
        new_password = credentials["password"]
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        user.password_changed_at = datetime.now(timezone.utc)
        user.failed_login_attempts = 0  # Reset failed attempts
        user.locked_until = None  # Unlock account
        
        self.db.commit()
        
        return {
            "new_password": new_password,
            "strength": credentials["strength"]
        }