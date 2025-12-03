from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class SupplierBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    whatsapp: Optional[str] = Field(None, max_length=50)
    
    # Address
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    
    # Business info
    fiscal_id: Optional[str] = Field(None, max_length=100)
    business_registration: Optional[str] = Field(None, max_length=100)
    vat_number: Optional[str] = Field(None, max_length=100)
    
    # Terms
    payment_terms: Optional[str] = Field(None, max_length=255)
    preferred_payment_method: Optional[str] = Field(None, max_length=100)
    shipping_terms: Optional[str] = Field(None, max_length=255)
    lead_time_days: int = Field(30, ge=0)
    
    # Status
    is_active: bool = True
    is_preferred: bool = False
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    whatsapp: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    fiscal_id: Optional[str] = Field(None, max_length=100)
    payment_terms: Optional[str] = Field(None, max_length=255)
    lead_time_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_preferred: Optional[bool] = None
    notes: Optional[str] = None

class SupplierResponse(SupplierBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    full_address: Optional[str] = None
    products_count: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class SupplierListResponse(BaseModel):
    suppliers: List[SupplierResponse]
    total: int

class SupplierNestedResponse(BaseModel):
    id: UUID
    company_name: str
    contact_person: Optional[str]
    email: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)