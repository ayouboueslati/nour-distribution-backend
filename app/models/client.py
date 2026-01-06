from sqlalchemy import Column, String, Text, Enum, Boolean, Float
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class ClientType(str, enum.Enum):
    B2B = "b2b"
    B2C = "b2c"

class Client(BaseModel):
    __tablename__ = "clients"
    
    type = Column(Enum(ClientType), nullable=False)
    
    # Common fields
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50), nullable=False)
    address = Column(Text)
    
    # B2B specific
    company_name = Column(String(255))
    fiscal_id = Column(String(100))  # Matricule fiscal
    payment_method = Column(String(100))
    
    # Financial Limits & Suspension
    credit_limit = Column(Float, default=0.0) # 0 means no limit or not set
    current_balance = Column(Float, default=0.0) # Outstanding debt
    is_suspended = Column(Boolean, default=False)
    suspension_reason = Column(String(255), nullable=True)
    
    # B2C specific
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    # Preferences
    preferred_contact_method = Column(String(50))  # email, phone, whatsapp
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    orders = relationship("Order", back_populates="client")
    documents = relationship("Document", back_populates="client")
    
    def __repr__(self):
        name = self.company_name if self.type == ClientType.B2B else f"{self.first_name} {self.last_name}"
        return f"<Client {name} ({self.type.value})>"