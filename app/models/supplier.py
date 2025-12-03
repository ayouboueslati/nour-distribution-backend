from sqlalchemy import Column, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel

class Supplier(BaseModel):
    __tablename__ = "suppliers"
    
    # Company Information
    company_name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255))  # Legal business name
    
    # Contact Information
    contact_person = Column(String(255))
    email = Column(String(255), index=True)
    phone = Column(String(50))
    whatsapp = Column(String(50))  # Important for international suppliers
    
    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    
    # Business Information
    fiscal_id = Column(String(100), index=True)  # Tax ID/Matricule Fiscal
    business_registration = Column(String(100))  # Business registration number
    vat_number = Column(String(100))  # VAT/TVA number
    
    # Payment & Shipping Terms
    payment_terms = Column(String(255))  # Net 30, Net 60, etc.
    preferred_payment_method = Column(String(100))
    shipping_terms = Column(String(255))
    lead_time_days = Column(Integer, default=30)  # Average delivery time
    
    # Supplier Rating & Performance
    reliability_rating = Column(Integer, default=5)  # 1-5 scale
    quality_rating = Column(Integer, default=5)  # 1-5 scale
    communication_rating = Column(Integer, default=5)  # 1-5 scale
    
    # Status
    is_active = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)  # Preferred supplier
    
    # Additional Information
    notes = Column(Text)
    tags = Column(JSON)  # ["hair_brazilian", "premium_quality", etc.]
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    #{purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    
    @property
    def full_address(self):
        """Formatted full address"""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.extend([self.city, self.state, self.postal_code, self.country])
        return ", ".join(filter(None, parts))
    
    def __repr__(self):
        return f"<Supplier {self.company_name}>"