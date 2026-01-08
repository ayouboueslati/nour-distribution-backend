from pydantic import BaseModel, Field, ConfigDict, model_validator
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

class PaymentTermsEnum(str, Enum):
    IMMEDIATE = "immediate"  # Paiement immédiat
    NET30 = "net30"          # Paiement à 30 jours
    NET60 = "net60"          # Paiement à 60 jours
    ON_DELIVERY = "on_delivery" # Paiement à la livraison

class AvoirReasonEnum(str, Enum):
    RETURN = "return"        # Retour de marchandise
    DAMAGED = "damaged"      # Marchandise endommagée
    ERROR = "error"          # Erreur de facturation
    CANCELLATION = "cancellation" # Annulation de commande
    OTHER = "other"          # Autre raison

class DocumentStatusEnum(str, Enum):
    BROUILLON = "brouillon"
    EN_ATTENTE = "en_attente"
    ACCEPTE = "accepte"
    FACTURE = "facture"
    PAYE = "paye"
    ANNULE = "annule"
    REFUSE = "refuse"

class PaymentStatusEnum(str, Enum):
    NON_PAYE = "non_paye"
    PARTIEL = "partiel"
    PAYE = "paye"
    EN_RETARD = "en_retard"

class PaymentMethodEnum(str, Enum):
    CASH = "especes"           # Espèces (cash)
    CHECK = "cheque"           # Chèque
    BANK_TRANSFER = "virement" # Virement bancaire
    CARD = "carte"            # Carte bancaire
    POSTAL = "postal"         # Mandat postal
    MOBILE = "mobile"         # Paiement mobile (Flooz, E-dinar, etc.)
    OTHER = "autre"           # Autre  

# Document Item Schemas
class DocumentItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    tax_percent: float = Field(default=0.0, ge=0, le=100)

class DocumentItemUpdate(BaseModel):
    id: Optional[UUID] = None
    product_id: Optional[UUID] = None
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
    items: Optional[List[DocumentItemUpdate]] = Field(default_factory=list)
    
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    payment_terms: Optional[PaymentTermsEnum] = None
    payment_deadline: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    avoir_reason: Optional[AvoirReasonEnum] = None
    
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
    
    # New Fields
    payment_terms: Optional[PaymentTermsEnum] = None
    payment_deadline: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    avoir_reason: Optional[AvoirReasonEnum] = None
    
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
    payment_method: PaymentMethodEnum
    payment_date: datetime
    reference_number: Optional[str] = None
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_id: UUID
    amount: float
    payment_method: PaymentMethodEnum
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

# Document Summary (lightweight)
class DocumentSummary(BaseModel):
    """Lightweight document summary for lists"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_number: str
    type: DocumentTypeEnum
    status: DocumentStatusEnum
    version: int
    is_latest_version: bool
    issue_date: datetime
    total_amount: float
    created_at: datetime
    updated_at: datetime

# Devis Timeline Event
class DevisTimelineEvent(BaseModel):
    """Timeline event for devis tracking"""
    event_type: str  # 'created', 'modified', 'accepted', 'converted_to_facture', 'cancelled'
    devis_id: UUID
    devis_number: str
    version: int
    timestamp: datetime
    changed_by: Optional[UUID] = None
    description: str
    total_amount: Optional[float] = None
    status: DocumentStatusEnum

# Paginated Devis List Response
class PaginatedDevisResponse(BaseModel):
    """Paginated list of devis for an order"""
    devis_list: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

# Avoir (Credit Note) specific schema
class AvoirFromFacture(BaseModel):
    """Create an avoir from a facture"""
    facture_id: UUID
    items: Optional[List[DocumentItemCreate]] = Field(default_factory=list)
    reason: Optional[str] = None
    avoir_reason: Optional[str] = None # For frontend compatibility
    total_amount: Optional[float] = None # For itemless avoirs
    issue_date: Optional[datetime] = None
    notes: Optional[str] = None

    @model_validator(mode='after')
    def consolidate_fields(self) -> 'AvoirFromFacture':
        if not self.reason and self.avoir_reason:
            self.reason = self.avoir_reason
        if not self.reason:
            self.reason = "return" # Default
        return self