from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import BaseModel

class Category(BaseModel):
    __tablename__ = "categories"
    
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    slug = Column(String(255), unique=True, index=True)  # URL-friendly name
    
    # Hierarchical categories
    parent_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    
    # Display properties
    image_url = Column(String(500))  # Category image
    sort_order = Column(Integer, default=0)  # For manual ordering
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Featured on homepage
    
    # Relationships
    parent = relationship("Category", remote_side="Category.id", backref="subcategories")
    products = relationship("Product", back_populates="category")
    
    def __repr__(self):
        return f"<Category {self.name}>"