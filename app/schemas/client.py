from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class ClientTypeEnum(str, Enum):
    B2B = "b2b"
    B2C = "b2c"

# Client Schemas
class ClientCreate(BaseModel):
    type: ClientTypeEnum
    
    # Common fields
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: str
    address: Optional[str] = None
    
    # B2B specific
    company_name: Optional[str] = None
    fiscal_id: Optional[str] = None
    payment_method: Optional[str] = None
    
    # B2C specific
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Preferences
    preferred_contact_method: Optional[str] = None
    notes: Optional[str] = None

class B2CCheckoutData(BaseModel):
    """B2C client data for checkout"""
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    address: str
    delivery_notes: Optional[str] = None
    preferred_contact: Optional[str] = 'phone'

class B2BCheckoutData(BaseModel):
    """B2B client data for checkout"""
    company_name: str
    fiscal_id: str
    contact_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    address: str
    payment_method: Optional[str] = 'virement'
    notes: Optional[str] = None

class GuestCheckoutRequest(BaseModel):
    """Schema for guest checkout - matches frontend structure"""
    is_company: bool
    b2c_data: Optional[B2CCheckoutData] = None
    b2b_data: Optional[B2BCheckoutData] = None

class ClientUpdate(BaseModel):
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    company_name: Optional[str] = None
    fiscal_id: Optional[str] = None
    payment_method: Optional[str] = None
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    preferred_contact_method: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    type: ClientTypeEnum
    
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: str
    address: Optional[str] = None
    
    company_name: Optional[str] = None
    fiscal_id: Optional[str] = None
    payment_method: Optional[str] = None
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    preferred_contact_method: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    
    created_at: datetime
    updated_at: datetime

class ClientListResponse(BaseModel):
    clients: List[ClientResponse]
    total: int
    page: int = 1
    page_size: int = 100