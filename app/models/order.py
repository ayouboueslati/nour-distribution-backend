from sqlalchemy import Column, String, Text, Integer, Float, Enum, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel
from sqlalchemy.dialects.postgresql import UUID
import enum

class OrderStatus(enum.Enum):
    EN_ATTENTE = "en_attente"  # Waiting - just submitted by client
    EN_TRAITEMENT = "en_traitement"  # Processing - admin is working on it
    CONFIRME = "confirme"  # Confirmed by admin
    ANNULE = "annule"  # Cancelled

class Order(BaseModel):
    __tablename__ = "orders"
    
    # Order identification
    order_number = Column(String(50), unique=True, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.EN_ATTENTE)
    
    # Client relationship
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    client = relationship("Client", back_populates="orders")
    
    # Order timeline
    submitted_at = Column(DateTime(timezone=True))  # When client submitted
    processed_at = Column(DateTime(timezone=True))  # When admin started processing
    confirmed_at = Column(DateTime(timezone=True))  # When admin confirmed
    
    # Pricing (set by admin during processing)
    subtotal = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    # Delivery info
    shipping_address = Column(Text)
    delivery_notes = Column(Text)
    
    # Admin notes
    internal_notes = Column(Text)
    
    # Stock reservation tracking
    stock_reserved = Column(Boolean, default=False)
    reservation_expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="order")
    history = relationship("OrderHistory", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order {self.order_number} ({self.status.value})>"


class OrderItem(BaseModel):
    __tablename__ = "order_items"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=True)  # Set by admin when pricing
    discount_percent = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem {self.product.name if hasattr(self, 'product') else self.product_id} x {self.quantity}>"


class OrderHistory(BaseModel):
    __tablename__ = "order_history"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    
    # Change tracking
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100))  # "status_changed", "items_modified", "pricing_updated", etc.
    old_value = Column(Text)
    new_value = Column(Text)
    notes = Column(Text)
    
    # Relationships
    order = relationship("Order", back_populates="history")
    user = relationship("User")
    
    def __repr__(self):
        return f"<OrderHistory {self.action} on {self.order_id}>"