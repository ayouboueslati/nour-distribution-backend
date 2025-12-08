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