from sqlalchemy import Column, String, Text, Integer, Float, Enum, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
import enum

class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"         # Created, waiting for shipment
    SHIPPED = "shipped"         # Leaving warehouse
    DELIVERED = "delivered"     # Received by client
    RETURNED = "returned"       # Returned to warehouse
    FAILED = "failed"           # Delivery failed

class DeliveryNote(BaseModel):
    __tablename__ = "delivery_notes"
    
    delivery_number = Column(String(50), unique=True, index=True)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING)
    
    # Relationships
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    
    # Optional link to a Facture if generated simultaneously
    facture_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    
    # Logistics
    shipped_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    
    carrier_name = Column(String(100))
    tracking_reference = Column(String(100))
    shipping_address = Column(Text)
    
    # Notes
    notes = Column(Text)
    
    # Relationships
    order = relationship("Order", backref="deliveries")
    client = relationship("Client")
    facture = relationship("Document") # linked facture
    items = relationship("DeliveryNoteItem", back_populates="delivery_note", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DeliveryNote {self.delivery_number} ({self.status.value})>"


class DeliveryNoteItem(BaseModel):
    __tablename__ = "delivery_note_items"
    
    delivery_note_id = Column(UUID(as_uuid=True), ForeignKey("delivery_notes.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    # Snapshot of product details
    product_name = Column(String(255))
    product_sku = Column(String(100))
    
    quantity = Column(Integer, nullable=False)
    
    # Relationships
    delivery_note = relationship("DeliveryNote", back_populates="items")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<DeliveryNoteItem {self.product_name} x {self.quantity}>"
