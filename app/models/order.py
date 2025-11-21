from sqlalchemy import Column, String, Text, Integer, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel
from sqlalchemy.dialects.postgresql import UUID
import enum

class OrderStatus(enum.Enum):
    DRAFT = "draft"  # Submitted by customer, waiting for pricing
    PENDING = "pending"  # Priced by admin, waiting for client confirmation
    CONFIRMED = "confirmed"  # Client confirmed, ready for processing
    PROCESSING = "processing"  # Being prepared
    SHIPPED = "shipped"  # Sent to client
    DELIVERED = "delivered"  # Completed
    CANCELLED = "cancelled"

class Order(BaseModel):
    __tablename__ = "orders"
    
    # Order identification
    order_number = Column(String(50), unique=True, index=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    
    # Client relationship
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    client = relationship("Client", back_populates="orders")
    
    # Order details
    submitted_at = Column(DateTime(timezone=True))  # When customer submitted
    priced_at = Column(DateTime(timezone=True))  # When admin added prices
    confirmed_at = Column(DateTime(timezone=True))  # When client confirmed
    
    # Pricing (set by admin)
    subtotal = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    # Delivery info
    shipping_address = Column(Text)
    delivery_notes = Column(Text)
    
    # Admin notes
    internal_notes = Column(Text)
    
    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="order")
    
    def __repr__(self):
        return f"<Order {self.order_number} ({self.status.value})>"

class OrderItem(BaseModel):
    __tablename__ = "order_items"
    
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float)  # Set by admin when pricing the order
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem {self.product.name} x {self.quantity}>"