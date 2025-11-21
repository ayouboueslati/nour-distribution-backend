from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel
from sqlalchemy.dialects.postgresql import UUID

class Product(BaseModel):
    __tablename__ = "products"
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), unique=True, index=True)
    
    # Inventory
    stock_quantity = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    
    # Supplier
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="products")
    
    # Pricing (hidden from customers)
    cost_price = Column(Float)  # Prix d'achat
    suggested_price = Column(Float)  # Prix de vente suggéré
    
    # Product details
    length = Column(String(50))  # 24", 26", etc.
    texture = Column(String(100))  # Brésilien, Malaisie, etc.
    color = Column(String(100))
    
    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product {self.name} (Stock: {self.stock_quantity})>"