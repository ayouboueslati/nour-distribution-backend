from sqlalchemy import Column, String, Integer, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
import enum

class MovementType(enum.Enum):
    STOCK_IN = "stock_in"  # Restock, purchase
    STOCK_OUT = "stock_out"  # Sale, damage, adjustment
    RESERVED = "reserved"  # Reserved for orders
    RELEASED = "released"  # Released from reservation

class InventoryMovement(BaseModel):
    __tablename__ = "inventory_movements"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    
    # Reference information
    reference_type = Column(String(100))  # "order", "purchase", "adjustment"
    reference_id = Column(UUID(as_uuid=True))  # ID of the related document
    
    # Reason and notes
    reason = Column(String(255))  # "sale", "restock", "damage", "adjustment"
    notes = Column(Text)
    
    # Performed by
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # User who made the change
    
    # Relationships
    product = relationship("Product", back_populates="inventory_movements")
    user = relationship("User")
    
    def __repr__(self):
        return f"<InventoryMovement {self.movement_type.value} {self.quantity} for {self.product_id}>"