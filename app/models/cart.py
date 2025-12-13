from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
from datetime import datetime

class Cart(BaseModel):
    __tablename__ = "carts"
    
    # Remove client_id completely
    # Use guest_session_id for identifying carts instead
    guest_session_id = Column(String(255), nullable=True, index=True)
    
    # Cart status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Cart {self.id} - Guest {self.guest_session_id}>"

class CartItem(BaseModel):
    __tablename__ = "cart_items"
    
    cart_id = Column(UUID(as_uuid=True), ForeignKey("carts.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    
    # Temporary stock reservation
    reserved_at = Column(DateTime(timezone=True))
    reservation_expires_at = Column(DateTime(timezone=True))  # 30 days from reserved_at
    
    # Relationships
    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")
    
    @property
    def is_reservation_expired(self):
        """Check if reservation has expired"""
        if not self.reservation_expires_at:
            return False
        return datetime.utcnow() > self.reservation_expires_at
    
    def __repr__(self):
        return f"<CartItem {self.product_id} x {self.quantity}>"
