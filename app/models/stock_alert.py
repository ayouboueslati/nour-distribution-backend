from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
import enum
from datetime import datetime

class AlertType(str, enum.Enum):
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    OVERSTOCK = "overstock"
    EXPIRING_RESERVATION = "expiring_reservation"
    STOCK_DISCREPANCY = "stock_discrepancy"

class AlertPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class StockAlert(BaseModel):
    __tablename__ = "stock_alerts"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    priority = Column(Enum(AlertPriority), nullable=False)
    message = Column(Text, nullable=False)
    threshold_value = Column(Integer, nullable=True)  # Expected threshold
    current_value = Column(Integer, nullable=False)   # Actual current value
    
    is_active = Column(Boolean, default=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="stock_alerts")
    acknowledger = relationship("User", foreign_keys=[acknowledged_by])
    
    def __repr__(self):
        return f"<StockAlert {self.alert_type.value} for {self.product_id} - {self.priority.value}>"
