from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel
from sqlalchemy.ext.hybrid import hybrid_property

class Product(BaseModel):
    __tablename__ = "products"
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    short_description = Column(String(500))  # For product cards
    
    # Identifiers
    sku = Column(String(100), unique=True, index=True)
    barcode = Column(String(100), unique=True, index=True)
    
    # Categorization
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    
    # Hair-Specific Attributes
    hair_type = Column(String(100))  # Brazilian, Malaysian, Peruvian, etc.
    hair_texture = Column(String(100))  # Straight, Wavy, Curly, Kinky
    hair_length = Column(String(50))  # 24", 26", 28", etc.
    hair_color = Column(String(100))  # Natural Black, Jet Black, Burgundy, etc.
    hair_origin = Column(String(100))  # Country of origin
    hair_quality = Column(String(100))  # Premium, Standard, Economy
    
    # Packaging
    weight_grams = Column(Integer)  # Weight in grams
    bundle_pieces = Column(Integer, default=1)  # Number of pieces in a bundle
    package_dimensions = Column(String(100))  # L x W x H
    
    # Inventory Management
    stock_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)  # For pending orders
    min_stock_level = Column(Integer, default=5)
    max_stock_level = Column(Integer)  # For restock alerts
    
    # Pricing (Hidden from customers)
    cost_price = Column(Numeric(10, 2))  # Purchase price from supplier
    wholesale_price = Column(Numeric(10, 2))  # Price for B2B customers
    retail_price = Column(Numeric(10, 2))  # Price for B2C customers (future use)
    
    # Supplier Information
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    supplier_sku = Column(String(100))  # Supplier's product code
    
    # Status & Visibility
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_best_seller = Column(Boolean, default=False)
    is_new_arrival = Column(Boolean, default=True)
    
    # Media
    main_image = Column(String(500))  # Primary product image
    additional_images = Column(JSON)  # List of additional image URLs
    
    # SEO & Marketing
    meta_title = Column(String(255))
    meta_description = Column(Text)
    search_keywords = Column(Text)  # Comma-separated keywords
    
    # Relationships
    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    inventory_movements = relationship("InventoryMovement", back_populates="product")
    stock_alerts = relationship("StockAlert", back_populates="product", cascade="all, delete-orphan")
    
    @hybrid_property
    def available_quantity(self):
        """Available stock after reserving for pending orders"""
        return self.stock_quantity - self.reserved_quantity
    
    @hybrid_property
    def needs_restock(self):
        """Check if product needs restocking"""
        return self.available_quantity <= self.min_stock_level
    
    def __repr__(self):
        return f"<Product {self.name} ({self.sku})>"