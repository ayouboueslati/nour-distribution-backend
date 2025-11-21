from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel

class Supplier(BaseModel):
    __tablename__ = "suppliers"
    
    name = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    
    # Address
    address = Column(Text)
    city = Column(String(100))
    country = Column(String(100))
    
    # Business info
    fiscal_id = Column(String(100))
    payment_terms = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    
    def __repr__(self):
        return f"<Supplier {self.name}>"