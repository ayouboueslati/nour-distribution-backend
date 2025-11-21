from sqlalchemy import Column, String, Text, Float, Enum, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel
from sqlalchemy.dialects.postgresql import UUID
import enum

class DocumentType(enum.Enum):
    DEVIS = "devis"  # Quote
    FACTURE = "facture"  # Invoice
    AVOIR = "avoir"  # Credit note
    BON_LIVRAISON = "bon_livraison"  # Delivery note

class DocumentStatus(enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class Document(BaseModel):
    __tablename__ = "documents"
    
    # Document identification
    type = Column(Enum(DocumentType), nullable=False)
    document_number = Column(String(100), unique=True, index=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)
    
    # Relationships
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    
    client = relationship("Client", back_populates="documents")
    order = relationship("Order", back_populates="documents")
    
    # Dates
    issue_date = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    
    # Pricing
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    # Document details
    notes = Column(Text)
    terms = Column(Text)
    
    # PDF storage
    pdf_path = Column(String(500))  # Path to generated PDF
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    
    # Reference to other documents (for avoir -> facture linking)
    reference_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    reference_document = relationship("Document", remote_side="Document.id", backref="related_documents")
    
    def __repr__(self):
        return f"<{self.type.value.capitalize()} {self.document_number}>"