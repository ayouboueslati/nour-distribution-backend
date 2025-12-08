from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
import json

from app.models.document import (
    Document, DocumentItem, DocumentHistory, Payment,
    DocumentType, DocumentStatus, PaymentStatus
)
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.client import Client
from app.models.inventory import InventoryMovement, MovementType
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DevisFromOrder,
    DocumentItemCreate, PaymentCreate, AvoirFromFacture
)
from app.services.base import BaseService

class DocumentService(BaseService[Document]):
    def __init__(self, db: Session):
        super().__init__(Document, db)
    
    def generate_document_number(self, doc_type: DocumentType) -> str:
        """Generate unique document number"""
        now = datetime.now()
        
        prefix_map = {
            DocumentType.DEVIS: "DEV",
            DocumentType.FACTURE: "FACT",
            DocumentType.AVOIR: "AV"
        }
        
        prefix = f"{prefix_map[doc_type]}-{now.strftime('%Y%m%d')}"
        
        # Get last document number for today
        last_doc = self.db.query(Document).filter(
            and_(
                Document.type == doc_type,
                Document.document_number.like(f"{prefix}%")
            )
        ).order_by(desc(Document.document_number)).first()
        
        if last_doc:
            last_num = int(last_doc.document_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
    def create_devis_from_order(
        self, 
        order_id: UUID, 
        devis_data: DevisFromOrder, 
        user_id: Optional[UUID] = None
    ) -> Document:
        """Create a devis from a confirmed order"""
        order = self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.client)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if not order.total_amount or order.total_amount == 0:
            raise ValueError("Order must have pricing before creating devis")
        
        # Create devis
        devis = Document(
            type=DocumentType.DEVIS,
            document_number=self.generate_document_number(DocumentType.DEVIS),
            status=DocumentStatus.EN_ATTENTE,
            client_id=order.client_id,
            order_id=order.id,
            issue_date=devis_data.issue_date,
            due_date=devis_data.due_date,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            discount=order.discount,
            shipping_fee=order.shipping_fee,
            total_amount=order.total_amount,
            payment_status=PaymentStatus.NON_PAYE,
            paid_amount=0.0,
            remaining_amount=order.total_amount,
            notes=devis_data.notes,
            terms=devis_data.terms,
            version=1,
            is_latest_version=True
        )
        self.db.add(devis)
        self.db.flush()
        
        # Create devis items from order items
        for order_item in order.items:
            devis_item = DocumentItem(
                document_id=devis.id,
                product_id=order_item.product_id,
                product_name=order_item.product.name,
                product_sku=order_item.product.sku,
                description=order_item.product.short_description,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                discount_percent=order_item.discount_percent,
                tax_percent=0.0,  # Calculate if needed
                subtotal=order_item.subtotal
            )
            self.db.add(devis_item)
        
        # Create history
        history = DocumentHistory(
            document_id=devis.id,
            changed_by=user_id,
            action="created",
            description=f"Devis created from order {order.order_number}",
            new_value=json.dumps({"status": DocumentStatus.EN_ATTENTE.value})
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(devis)
        return devis
    
    def create_document(
        self, 
        document_data: DocumentCreate, 
        user_id: Optional[UUID] = None
    ) -> Document:
        """Create a document (devis, facture, or avoir) directly"""
        # Verify client
        client = self.db.query(Client).filter(Client.id == document_data.client_id).first()
        if not client:
            raise ValueError("Client not found")
        
        # Create document
        document = Document(
            type=document_data.type,
            document_number=self.generate_document_number(document_data.type),
            status=DocumentStatus.BROUILLON,
            client_id=document_data.client_id,
            order_id=document_data.order_id,
            issue_date=document_data.issue_date,
            due_date=document_data.due_date,
            subtotal=document_data.subtotal,
            tax_amount=document_data.tax_amount,
            discount=document_data.discount,
            shipping_fee=document_data.shipping_fee,
            total_amount=document_data.total_amount,
            payment_status=PaymentStatus.NON_PAYE,
            paid_amount=0.0,
            remaining_amount=document_data.total_amount,
            notes=document_data.notes,
            terms=document_data.terms,
            version=1,
            is_latest_version=True
        )
        self.db.add(document)
        self.db.flush()
        
        # Create document items
        for item_data in document_data.items:
            product = self.db.query(Product).filter(Product.id == item_data.product_id).first()
            
            doc_item = DocumentItem(
                document_id=document.id,
                product_id=item_data.product_id,
                product_name=product.name if product else "Unknown",
                product_sku=product.sku if product else "",
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                discount_percent=item_data.discount_percent,
                tax_percent=item_data.tax_percent,
                subtotal=item_data.quantity * item_data.unit_price * (1 - item_data.discount_percent / 100)
            )
            self.db.add(doc_item)
        
        # Create history
        history = DocumentHistory(
            document_id=document.id,
            changed_by=user_id,
            action="created",
            description=f"{document.type.value.capitalize()} created",
            new_value=json.dumps({"status": DocumentStatus.BROUILLON.value})
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(document)
        return document
    
    def update_document(
        self, 
        document_id: UUID, 
        update_data: DocumentUpdate, 
        user_id: Optional[UUID] = None
    ) -> Document:
        """Update document (modify devis, facture, etc.)"""
        document = self.db.query(Document).options(
            joinedload(Document.items)
        ).filter(Document.id == document_id).first()
        
        if not document:
            raise ValueError("Document not found")
        
        # Check if document can be modified
        if document.type == DocumentType.FACTURE and document.status == DocumentStatus.PAYE:
            raise ValueError("Cannot modify a paid facture")
        
        # Store old values for history
        old_values = {
            "status": document.status.value if document.status else None,
            "total_amount": document.total_amount
        }
        
        # Create new version if significant changes
        create_new_version = False
        if update_data.items or (update_data.total_amount and update_data.total_amount != document.total_amount):
            create_new_version = True
        
        if create_new_version:
            # Mark current version as not latest
            document.is_latest_version = False
            
            # Create new version (duplicate with changes)
            new_document = Document(
                type=document.type,
                document_number=document.document_number,
                status=document.status,
                client_id=document.client_id,
                order_id=document.order_id,
                issue_date=document.issue_date,
                due_date=update_data.due_date if update_data.due_date else document.due_date,
                subtotal=update_data.subtotal if update_data.subtotal is not None else document.subtotal,
                tax_amount=update_data.tax_amount if update_data.tax_amount is not None else document.tax_amount,
                discount=update_data.discount if update_data.discount is not None else document.discount,
                shipping_fee=update_data.shipping_fee if update_data.shipping_fee is not None else document.shipping_fee,
                total_amount=update_data.total_amount if update_data.total_amount is not None else document.total_amount,
                payment_status=document.payment_status,
                paid_amount=document.paid_amount,
                remaining_amount=document.remaining_amount,
                notes=update_data.notes if update_data.notes else document.notes,
                terms=update_data.terms if update_data.terms else document.terms,
                reference_document_id=document.id,
                version=document.version + 1,
                is_latest_version=True
            )
            self.db.add(new_document)
            self.db.flush()
            
            # Copy or update items
            if update_data.items:
                # Create new items from update data
                for item_update in update_data.items:
                    # Find corresponding old item
                    old_item = next((item for item in document.items if item.id == item_update.id), None)
                    if old_item:
                        new_item = DocumentItem(
                            document_id=new_document.id,
                            product_id=old_item.product_id,
                            product_name=old_item.product_name,
                            product_sku=old_item.product_sku,
                            quantity=item_update.quantity if item_update.quantity else old_item.quantity,
                            unit_price=item_update.unit_price if item_update.unit_price else old_item.unit_price,
                            discount_percent=item_update.discount_percent if item_update.discount_percent is not None else old_item.discount_percent,
                            tax_percent=item_update.tax_percent if item_update.tax_percent is not None else old_item.tax_percent,
                            subtotal=old_item.subtotal
                        )
                        self.db.add(new_item)
            else:
                # Copy all items
                for old_item in document.items:
                    new_item = DocumentItem(
                        document_id=new_document.id,
                        product_id=old_item.product_id,
                        product_name=old_item.product_name,
                        product_sku=old_item.product_sku,
                        quantity=old_item.quantity,
                        unit_price=old_item.unit_price,
                        discount_percent=old_item.discount_percent,
                        tax_percent=old_item.tax_percent,
                        subtotal=old_item.subtotal
                    )
                    self.db.add(new_item)
            
            # Create history for new version
            history = DocumentHistory(
                document_id=new_document.id,
                changed_by=user_id,
                action="version_created",
                description=f"New version {new_document.version} created",
                old_value=json.dumps(old_values),
                new_value=json.dumps({
                    "version": new_document.version,
                    "total_amount": new_document.total_amount
                })
            )
            self.db.add(history)
            
            self.db.commit()
            self.db.refresh(new_document)
            return new_document
        else:
            # Simple update without versioning
            if update_data.status:
                document.status = update_data.status
            if update_data.notes:
                document.notes = update_data.notes
            if update_data.terms:
                document.terms = update_data.terms
            
            # Create history
            history = DocumentHistory(
                document_id=document.id,
                changed_by=user_id,
                action="updated",
                description="Document updated",
                old_value=json.dumps(old_values),
                new_value=json.dumps({
                    "status": document.status.value if document.status else None
                })
            )
            self.db.add(history)
            
            self.db.commit()
            self.db.refresh(document)
            return document
    
    def accept_devis(self, devis_id: UUID, user_id: Optional[UUID] = None) -> Document:
        """Accept a devis"""
        devis = self.db.query(Document).filter(
            and_(
                Document.id == devis_id,
                Document.type == DocumentType.DEVIS
            )
        ).first()
        
        if not devis:
            raise ValueError("Devis not found")
        
        if devis.status not in [DocumentStatus.EN_ATTENTE, DocumentStatus.BROUILLON]:
            raise ValueError("Devis cannot be accepted in current status")
        
        old_status = devis.status
        devis.status = DocumentStatus.ACCEPTE
        devis.accepted_date = datetime.utcnow()
        
        # Create history
        history = DocumentHistory(
            document_id=devis.id,
            changed_by=user_id,
            action="accepted",
            description="Devis accepted",
            old_value=old_status.value,
            new_value=DocumentStatus.ACCEPTE.value
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(devis)
        return devis
    
    def convert_devis_to_facture(self, devis_id: UUID, user_id: Optional[UUID] = None) -> Document:
        """Convert an accepted devis to a facture"""
        devis = self.db.query(Document).options(
            joinedload(Document.items)
        ).filter(
            and_(
                Document.id == devis_id,
                Document.type == DocumentType.DEVIS
            )
        ).first()
        
        if not devis:
            raise ValueError("Devis not found")
        
        if devis.status != DocumentStatus.ACCEPTE:
            raise ValueError("Devis must be accepted before converting to facture")
        
        # Create facture from devis
        facture = Document(
            type=DocumentType.FACTURE,
            document_number=self.generate_document_number(DocumentType.FACTURE),
            status=DocumentStatus.EN_ATTENTE,
            client_id=devis.client_id,
            order_id=devis.order_id,
            issue_date=datetime.utcnow(),
            due_date=devis.due_date,
            subtotal=devis.subtotal,
            tax_amount=devis.tax_amount,
            discount=devis.discount,
            shipping_fee=devis.shipping_fee,
            total_amount=devis.total_amount,
            payment_status=PaymentStatus.NON_PAYE,
            paid_amount=0.0,
            remaining_amount=devis.total_amount,
            notes=devis.notes,
            terms=devis.terms,
            reference_document_id=devis.id,
            version=1,
            is_latest_version=True
        )
        self.db.add(facture)
        self.db.flush()
        
        # Copy items from devis
        for devis_item in devis.items:
            facture_item = DocumentItem(
                document_id=facture.id,
                product_id=devis_item.product_id,
                product_name=devis_item.product_name,
                product_sku=devis_item.product_sku,
                description=devis_item.description,
                quantity=devis_item.quantity,
                unit_price=devis_item.unit_price,
                discount_percent=devis_item.discount_percent,
                tax_percent=devis_item.tax_percent,
                subtotal=devis_item.subtotal
            )
            self.db.add(facture_item)
        
        # Update devis status
        devis.status = DocumentStatus.FACTURE
        
        # Create histories
        devis_history = DocumentHistory(
            document_id=devis.id,
            changed_by=user_id,
            action="converted_to_facture",
            description=f"Converted to facture {facture.document_number}",
            old_value=DocumentStatus.ACCEPTE.value,
            new_value=DocumentStatus.FACTURE.value
        )
        self.db.add(devis_history)
        
        facture_history = DocumentHistory(
            document_id=facture.id,
            changed_by=user_id,
            action="created_from_devis",
            description=f"Created from devis {devis.document_number}",
            new_value=json.dumps({"status": DocumentStatus.EN_ATTENTE.value})
        )
        self.db.add(facture_history)
        
        # Reduce actual stock (not just reserved) if order exists
        if devis.order_id:
            order = self.db.query(Order).options(
                joinedload(Order.items)
            ).filter(Order.id == devis.order_id).first()
            
            if order and order.stock_reserved:
                for item in order.items:
                    product = self.db.query(Product).filter(Product.id == item.product_id).first()
                    if product:
                        # Reduce both actual stock and reserved quantity
                        product.stock_quantity -= item.quantity
                        product.reserved_quantity = max(0, product.reserved_quantity - item.quantity)
                        
                        # Create inventory movement
                        movement = InventoryMovement(
                            product_id=product.id,
                            movement_type=MovementType.STOCK_OUT,
                            quantity=item.quantity,
                            previous_stock=product.stock_quantity + item.quantity,
                            new_stock=product.stock_quantity,
                            reference_type="facture",
                            reference_id=facture.id,
                            reason="sale",
                            notes=f"Stock sold via facture {facture.document_number}",
                            performed_by=user_id
                        )
                        self.db.add(movement)
                
                order.stock_reserved = False
        
        self.db.commit()
        self.db.refresh(facture)
        return facture
    
    def create_avoir_from_facture(
        self, 
        avoir_data: AvoirFromFacture, 
        user_id: Optional[UUID] = None
    ) -> Document:
        """Create an avoir (credit note) from a facture"""
        facture = self.db.query(Document).options(
            joinedload(Document.items)
        ).filter(
            and_(
                Document.id == avoir_data.facture_id,
                Document.type == DocumentType.FACTURE
            )
        ).first()
        
        if not facture:
            raise ValueError("Facture not found")
        
        # Calculate avoir total
        avoir_total = sum(
            item.quantity * item.unit_price * (1 - item.discount_percent / 100)
            for item in avoir_data.items
        )
        
        # Create avoir
        avoir = Document(
            type=DocumentType.AVOIR,
            document_number=self.generate_document_number(DocumentType.AVOIR),
            status=DocumentStatus.EN_ATTENTE,
            client_id=facture.client_id,
            order_id=facture.order_id,
            issue_date=datetime.utcnow(),
            subtotal=avoir_total,
            tax_amount=0.0,
            discount=0.0,
            shipping_fee=0.0,
            total_amount=avoir_total,
            payment_status=PaymentStatus.NON_PAYE,
            paid_amount=0.0,
            remaining_amount=avoir_total,
            notes=f"{avoir_data.reason}\n{avoir_data.notes or ''}",
            reference_document_id=facture.id,
            version=1,
            is_latest_version=True
        )
        self.db.add(avoir)
        self.db.flush()
        
        # Create avoir items
        for item_data in avoir_data.items:
            product = self.db.query(Product).filter(Product.id == item_data.product_id).first()
            
            avoir_item = DocumentItem(
                document_id=avoir.id,
                product_id=item_data.product_id,
                product_name=product.name if product else "Unknown",
                product_sku=product.sku if product else "",
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                discount_percent=item_data.discount_percent,
                tax_percent=item_data.tax_percent,
                subtotal=item_data.quantity * item_data.unit_price * (1 - item_data.discount_percent / 100)
            )
            self.db.add(avoir_item)
            
            # Return stock if needed
            if product:
                product.stock_quantity += item_data.quantity
                
                # Create inventory movement
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type=MovementType.STOCK_IN,
                    quantity=item_data.quantity,
                    previous_stock=product.stock_quantity - item_data.quantity,
                    new_stock=product.stock_quantity,
                    reference_type="avoir",
                    reference_id=avoir.id,
                    reason="return",
                    notes=f"Stock returned via avoir {avoir.document_number}",
                    performed_by=user_id
                )
                self.db.add(movement)
        
        # Update facture payment status if avoir affects it
        if avoir_total >= facture.remaining_amount:
            facture.payment_status = PaymentStatus.PAYE
            facture.remaining_amount = 0.0
        else:
            facture.remaining_amount -= avoir_total
        
        # Create histories
        avoir_history = DocumentHistory(
            document_id=avoir.id,
            changed_by=user_id,
            action="created_from_facture",
            description=f"Avoir created from facture {facture.document_number}. Reason: {avoir_data.reason}",
            new_value=json.dumps({"total_amount": avoir_total})
        )
        self.db.add(avoir_history)
        
        facture_history = DocumentHistory(
            document_id=facture.id,
            changed_by=user_id,
            action="avoir_created",
            description=f"Avoir {avoir.document_number} created for this facture",
            old_value=str(facture.remaining_amount + avoir_total),
            new_value=str(facture.remaining_amount)
        )
        self.db.add(facture_history)
        
        self.db.commit()
        self.db.refresh(avoir)
        return avoir
    
    def add_payment(
        self, 
        payment_data: PaymentCreate, 
        user_id: Optional[UUID] = None
    ) -> Payment:
        """Add a payment to a facture"""
        document = self.db.query(Document).filter(
            Document.id == payment_data.document_id
        ).first()
        
        if not document:
            raise ValueError("Document not found")
        
        if document.type != DocumentType.FACTURE:
            raise ValueError("Payments can only be added to factures")
        
        if payment_data.amount > document.remaining_amount:
            raise ValueError("Payment amount exceeds remaining amount")
        
        # Create payment
        payment = Payment(
            document_id=document.id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            payment_date=payment_data.payment_date,
            reference_number=payment_data.reference_number,
            notes=payment_data.notes,
            recorded_by=user_id
        )
        self.db.add(payment)
        
        # Update document payment status
        document.paid_amount += payment_data.amount
        document.remaining_amount -= payment_data.amount
        
        if document.remaining_amount == 0:
            document.payment_status = PaymentStatus.PAYE
            document.status = DocumentStatus.PAYE
        elif document.paid_amount > 0:
            document.payment_status = PaymentStatus.PARTIEL
        
        # Create history
        history = DocumentHistory(
            document_id=document.id,
            changed_by=user_id,
            action="payment_added",
            description=f"Payment of {payment_data.amount} added",
            new_value=json.dumps({
                "payment_amount": payment_data.amount,
                "remaining_amount": document.remaining_amount,
                "payment_status": document.payment_status.value
            })
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(payment)
        return payment
    
    def get_document_with_details(self, document_id: UUID) -> Optional[Document]:
        """Get document with all related data including history"""
        return self.db.query(Document).options(
            joinedload(Document.items),
            joinedload(Document.client),
            joinedload(Document.order),
            joinedload(Document.history).joinedload(DocumentHistory.user),
            joinedload(Document.payments)
        ).filter(Document.id == document_id).first()
    
    def get_document_versions(self, document_number: str) -> List[Document]:
        """Get all versions of a document"""
        return self.db.query(Document).filter(
            Document.document_number == document_number
        ).order_by(Document.version).all()
    
    def get_documents_by_type(
        self, 
        doc_type: DocumentType, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Document]:
        """Get documents filtered by type"""
        return self.db.query(Document).filter(
            and_(
                Document.type == doc_type,
                Document.is_latest_version == True
            )
        ).order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
    
    def get_client_documents(
        self, 
        client_id: UUID, 
        doc_type: Optional[DocumentType] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Document]:
        """Get all documents for a client"""
        query = self.db.query(Document).filter(
            and_(
                Document.client_id == client_id,
                Document.is_latest_version == True
            )
        )
        
        if doc_type:
            query = query.filter(Document.type == doc_type)
        
        return query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()