from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum
from app.schemas.client import ClientResponse
from app.schemas.user import UserResponse

# Enums
class DocumentTypeEnum(str, Enum):
    DEVIS = "devis"
    FACTURE = "facture"
    AVOIR = "avoir"

class DocumentStatusEnum(str, Enum):
    BROUILLON = "brouillon"
    EN_ATTENTE = "en_attente"
    ACCEPTE = "accepte"
    FACTURE = "facture"
    PAYE = "paye"
    ANNULE = "annule"

class PaymentStatusEnum(str, Enum):
    NON_PAYE = "non_paye"
    PARTIEL = "partiel"
    PAYE = "paye"
    EN_RETARD = "en_retard"

# Document Item Schemas
class DocumentItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    tax_percent: float = Field(default=0.0, ge=0, le=100)

class DocumentItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    discount_percent: Optional[float] = Field(None, ge=0, le=100)
    tax_percent: Optional[float] = Field(None, ge=0, le=100)

class DocumentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    description: Optional[str] = None
    quantity: int
    unit_price: float
    discount_percent: float
    tax_percent: float
    subtotal: float
    created_at: datetime

# Document Schemas
class DocumentCreate(BaseModel):
    type: DocumentTypeEnum
    client_id: UUID
    order_id: Optional[UUID] = None
    items: List[DocumentItemCreate]
    
    issue_date: datetime
    due_date: Optional[datetime] = None
    
    subtotal: float = Field(ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount: float = Field(default=0.0, ge=0)
    shipping_fee: float = Field(default=0.0, ge=0)
    total_amount: float = Field(ge=0)
    
    notes: Optional[str] = None
    terms: Optional[str] = None

class DevisFromOrder(BaseModel):
    """Create a devis from an order"""
    order_id: UUID
    issue_date: datetime
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    terms: Optional[str] = None

class DocumentUpdate(BaseModel):
    status: Optional[DocumentStatusEnum] = None
    items: Optional[List[DocumentItemUpdate]] = None
    
    subtotal: Optional[float] = Field(None, ge=0)
    tax_amount: Optional[float] = Field(None, ge=0)
    discount: Optional[float] = Field(None, ge=0)
    shipping_fee: Optional[float] = Field(None, ge=0)
    total_amount: Optional[float] = Field(None, ge=0)
    
    notes: Optional[str] = None
    terms: Optional[str] = None

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    type: DocumentTypeEnum
    document_number: str
    status: DocumentStatusEnum
    
    client_id: UUID
    order_id: Optional[UUID] = None
    
    issue_date: datetime
    due_date: Optional[datetime] = None
    accepted_date: Optional[datetime] = None
    
    subtotal: float
    tax_amount: float
    discount: float
    shipping_fee: float
    total_amount: float
    
    payment_status: PaymentStatusEnum
    paid_amount: float
    remaining_amount: float
    
    notes: Optional[str] = None
    terms: Optional[str] = None
    
    pdf_path: Optional[str] = None
    is_sent: bool
    sent_at: Optional[datetime] = None
    
    reference_document_id: Optional[UUID] = None
    version: int
    is_latest_version: bool
    
    created_at: datetime
    updated_at: datetime
    
    items: List[DocumentItemResponse] = []
    client: Optional[ClientResponse] = None

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 100

# Payment Schemas
class PaymentCreate(BaseModel):
    document_id: UUID
    amount: float = Field(gt=0)
    payment_method: str
    payment_date: datetime
    reference_number: Optional[str] = None
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_id: UUID
    amount: float
    payment_method: str
    payment_date: datetime
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: UUID
    created_at: datetime
    
    user: Optional[UserResponse] = None

# Document History Schemas
class DocumentHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_id: UUID
    changed_by: UUID
    action: str
    description: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    created_at: datetime
    
    user: Optional[UserResponse] = None

# Avoir (Credit Note) specific schema
class AvoirFromFacture(BaseModel):
    """Create an avoir from a facture"""
    facture_id: UUID
    items: List[DocumentItemCreate]  # Items to credit
    reason: str
    notes: Optional[str] = None