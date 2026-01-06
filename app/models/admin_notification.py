from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
import enum

class NotificationType(str, enum.Enum):
    STOCK_MOVEMENT = "stock_movement"
    STOCK_ALERT = "stock_alert"
    ORDER_STATUS = "order_status"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    AVOIR_CREATED = "avoir_created"
    FACTURE_CREATED = "facture_created"
    DEVIS_CREATED = "devis_created"

class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AdminNotification(BaseModel):
    __tablename__ = "admin_notifications"
    
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(Enum(NotificationPriority), nullable=False)
    
    # Target roles (stored as JSON array of role names)
    target_roles = Column(JSON, nullable=False, default=list)
    
    # Related entity (product, order, document, etc.)
    related_entity_type = Column(String(50), nullable=True)  # "product", "order", "document"
    related_entity_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Read tracking (JSON array of user IDs who have read this)
    is_read = Column(Boolean, default=False)
    read_by = Column(JSON, default=list)  # List of user UUIDs
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Creator
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<AdminNotification {self.notification_type.value} - {self.priority.value}>"
