from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum
import uuid
from datetime import datetime

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"

class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STAFF)
    is_active = Column(Boolean, default=True)
    
    last_login = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Audit trail
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    creator = relationship("User", remote_side="User.id", backref="created_users")

    # Security
    password_changed_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"

    @property
    def is_locked(self) -> bool:
        """Check if user account is temporarily locked."""
        return bool(self.locked_until and datetime.utcnow() < self.locked_until)

    def to_dict(self):
        """Convert to serializable dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
