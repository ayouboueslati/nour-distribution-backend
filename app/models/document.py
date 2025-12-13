from sqlalchemy import Column, String, Text, Float, Enum, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship
from .base import BaseModel
from sqlalchemy.dialects.postgresql import UUID
import enum

class DocumentType(enum.Enum):
    DEVIS = "devis"  # Quote
    FACTURE = "facture"  # Invoice
    AVOIR = "avoir"  # Credit note

class DocumentStatus(enum.Enum):
    BROUILLON = "brouillon"  # Draft
    EN_ATTENTE = "en_attente"  # Waiting for approval
    ACCEPTE = "accepte"  # Accepted
    FACTURE = "facture"  # Converted to invoice (for devis)
    PAYE = "paye"  # Paid
    ANNULE = "annule"  # Cancelled

class PaymentStatus(enum.Enum):
    NON_PAYE = "non_paye"  # Unpaid
    PARTIEL = "partiel"  # Partially paid
    PAYE = "paye"  # Fully paid
    EN_RETARD = "en_retard"  # Overdue

class Document(BaseModel):
    __tablename__ = "documents"
    
    # Document identification
    type = Column(Enum(DocumentType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    document_number = Column(String(100), unique=True, index=True)
    status = Column(Enum(DocumentStatus, values_callable=lambda x: [e.value for e in x]), default=DocumentStatus.BROUILLON)
    
    # Relationships
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    client = relationship("Client", back_populates="documents")
    order = relationship("Order", back_populates="documents")
    
    # Dates
    issue_date = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    accepted_date = Column(DateTime(timezone=True))  # When devis was accepted
    
    # Pricing
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    # Payment tracking (for factures)
    payment_status = Column(Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x]), default=PaymentStatus.NON_PAYE)
    paid_amount = Column(Float, default=0.0)
    remaining_amount = Column(Float, default=0.0)
    
    # Document details
    notes = Column(Text)
    terms = Column(Text)
    
    # PDF storage
    pdf_path = Column(String(500))
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    
    # Reference to other documents
    reference_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    reference_document = relationship("Document", remote_side="Document.id", foreign_keys=[reference_document_id], backref="related_documents")
    
    # Version tracking for modifications
    version = Column(Integer, default=1)
    is_latest_version = Column(Boolean, default=True)
    
    # Relationships
    items = relationship("DocumentItem", back_populates="document", cascade="all, delete-orphan")
    history = relationship("DocumentHistory", back_populates="document", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<{self.type.value.capitalize()} {self.document_number}>"


class DocumentItem(BaseModel):
    __tablename__ = "document_items"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    # Item details
    product_name = Column(String(255))  # Store name in case product is deleted
    product_sku = Column(String(100))
    description = Column(Text)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0.0)
    tax_percent = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    
    # Relationships
    document = relationship("Document", back_populates="items")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<DocumentItem {self.product_name} x {self.quantity}>"


class DocumentHistory(BaseModel):
    __tablename__ = "document_history"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    
    # Change tracking
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100))  # "created", "modified", "accepted", "converted_to_facture", etc.
    description = Column(Text)
    old_value = Column(Text)  # JSON of old state
    new_value = Column(Text)  # JSON of new state
    
    # Relationships
    document = relationship("Document", back_populates="history")
    user = relationship("User")
    
    def __repr__(self):
        return f"<DocumentHistory {self.action} on {self.document_id}>"


class Payment(BaseModel):
    __tablename__ = "payments"
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    
    # Payment details
    amount = Column(Float, nullable=False)
    payment_method = Column(String(100))  # cash, bank_transfer, check, etc.
    payment_date = Column(DateTime(timezone=True))
    reference_number = Column(String(100))  # Transaction/check number
    
    # Notes
    notes = Column(Text)
    
    # Recorded by
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    document = relationship("Document", back_populates="payments")
    user = relationship("User")
    
    def __repr__(self):
        return f"<Payment {self.amount} for {self.document_id}>"

class PaymentMethodEnum(str, Enum):
    CASH = "especes"           # Espèces (cash)
    CHECK = "cheque"           # Chèque
    BANK_TRANSFER = "virement" # Virement bancaire
    CARD = "carte"            # Carte bancaire
    POSTAL = "postal"         # Mandat postal
    MOBILE = "mobile"         # Paiement mobile (Flooz, E-dinar, etc.)
    OTHER = "autre"           # Autre  