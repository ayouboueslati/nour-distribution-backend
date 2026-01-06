from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
import json

from app.models.document import (
    Document, DocumentItem, DocumentHistory, Payment,
    DocumentType, DocumentStatus, PaymentStatus, PaymentTerms, AvoirReason
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
        now = datetime.now(timezone.utc)
        
        # Look up prefix by value to handle both Model Enums and Schema Enums
        prefix_map = {
            DocumentType.DEVIS.value: "DEV",
            DocumentType.FACTURE.value: "FACT",
            DocumentType.AVOIR.value: "AV"
        }
        
        # Ensure we use the value for lookup
        doc_type_value = doc_type.value if hasattr(doc_type, 'value') else doc_type
        
        if doc_type_value not in prefix_map:
            raise ValueError(f"Invalid document type: {doc_type}")
            
        prefix = f"{prefix_map[doc_type_value]}-{now.strftime('%Y%m%d')}"        
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
        """Create a devis from a confirmed order with ALL information"""
        order = self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.client)
        ).filter(Order.id == order_id).first()
    
        if not order:
            raise ValueError("Commande introuvable")
    
        # VALIDATION CRITIQUE : Vérifier que la commande a des prix
        if not order.total_amount or order.total_amount == 0:
            raise ValueError(
                f"Impossible de créer un devis : la commande {order.order_number} n'a pas de prix défini. "
                "Veuillez d'abord définir les prix des articles."
            )
    
        # Vérifier que tous les items ont des prix
        for item in order.items:
            if not item.unit_price or item.unit_price == 0:
                raise ValueError(
                    f"Impossible de créer un devis : le produit '{item.product.name}' n'a pas de prix défini. "
                    "Veuillez définir les prix avant de générer le devis."
                )
    
        # Vérifier le client
        if not order.client:
            raise ValueError("Commande sans client associé")
    
        print(f"📋 Creating devis for order {order.order_number}")
        print(f"   Client: {order.client.company_name if order.client.type == 'b2b' else f'{order.client.first_name} {order.client.last_name}'}")
        print(f"   Total: {order.total_amount} DT")
        print(f"   Items: {len(order.items)}")
    
        # Create devis
        devis = Document(
            type=DocumentType.DEVIS,
            document_number=self.generate_document_number(DocumentType.DEVIS),
            status=DocumentStatus.EN_ATTENTE,
            client_id=order.client_id,
            order_id=order.id,
            issue_date=devis_data.issue_date,
            due_date=devis_data.due_date,
        
        # PRIX ET TOTAUX (copiés depuis la commande)
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            discount=order.discount,
            shipping_fee=order.shipping_fee,
            total_amount=order.total_amount,
        
        # STATUT DE PAIEMENT
            payment_status=PaymentStatus.NON_PAYE,
            paid_amount=0.0,
            remaining_amount=order.total_amount,
        
        # NOTES ET CONDITIONS
            notes=devis_data.notes,
            terms=devis_data.terms,
        
        # VERSIONING
            version=1,
            is_latest_version=True,
            
            # New fields
            valid_until=devis_data.due_date, # Default validity to due date
        )
        self.db.add(devis)
        self.db.flush()
    
        print(f"✅ Devis {devis.document_number} created with ID: {devis.id}")
    
        # Créer les items du devis depuis les items de commande
        for order_item in order.items:
            print(f"   Adding item: {order_item.product.name} x{order_item.quantity} @ {order_item.unit_price} DT")
        
            devis_item = DocumentItem(
                document_id=devis.id,
                product_id=order_item.product_id,
                product_name=order_item.product.name,
                product_sku=order_item.product.sku,
                description=order_item.product.short_description or order_item.product.description,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                discount_percent=order_item.discount_percent,
                tax_percent=19.0,  # TVA Tunisia standard
                subtotal=order_item.subtotal
            )
            self.db.add(devis_item)
    
        # Créer l'historique
        history = DocumentHistory(
            document_id=devis.id,
            changed_by=user_id,
            action="created",
            description=f"Devis créé automatiquement depuis la commande {order.order_number}",
            new_value=json.dumps({
                "status": DocumentStatus.EN_ATTENTE.value,
                "order_number": order.order_number,
                "client_name": order.client.company_name if order.client.type == 'b2b' else f"{order.client.first_name} {order.client.last_name}",
                "client_email": order.client.email,
                "total_amount": float(order.total_amount),
                "items_count": len(order.items)
            })
        )
        self.db.add(history)
    
        self.db.commit()
        self.db.refresh(devis)
    
        print(f"🎉 Devis {devis.document_number} successfully created!")
        print(f"   Total: {devis.total_amount} DT")
        print(f"   Status: {devis.status.value}")
    
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
                    old_item = next((item for item in document.items if str(item.id) == str(item_update.id)), None)
                    if old_item:
                        qty = int(item_update.quantity if item_update.quantity is not None else old_item.quantity)
                        price = float(item_update.unit_price if item_update.unit_price is not None else old_item.unit_price)
                        disc = float(item_update.discount_percent if item_update.discount_percent is not None else old_item.discount_percent)
                        tax = float(item_update.tax_percent if item_update.tax_percent is not None else old_item.tax_percent)
                        
                        # Recalculate subtotal
                        item_subtotal = (float(qty) * price * (1 - disc / 100))
                        
                        new_item = DocumentItem(
                            document_id=new_document.id,
                            product_id=old_item.product_id,
                            product_name=old_item.product_name,
                            product_sku=old_item.product_sku,
                            quantity=qty,
                            unit_price=price,
                            discount_percent=disc,
                            tax_percent=tax,
                            subtotal=item_subtotal
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
        devis.accepted_date = datetime.now(timezone.utc)
        
        # Update parent Order status if exists
        if devis.order_id:
            from app.models.order import Order, OrderStatus
            order = self.db.query(Order).filter(Order.id == devis.order_id).first()
            if order and order.status != OrderStatus.CONFIRMED:
                print(f"🔄 Updating parent order {order.order_number} status to CONFIRMED")
                old_order_status = order.status
                order.status = OrderStatus.CONFIRMED
                order.confirmed_at = datetime.now(timezone.utc)
                
                # Add order history
                from app.models.order import OrderHistory
                order_history = OrderHistory(
                    order_id=order.id,
                    changed_by=user_id,
                    action="status_changed",
                    old_value=old_order_status.value,
                    new_value=OrderStatus.CONFIRMED.value,
                    notes=f"Auto-updated from Devis {devis.document_number} acceptance"
                )
                self.db.add(order_history)
        
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

    def reject_devis(self, devis_id: UUID, reason: str, user_id: Optional[UUID] = None) -> Document:
        """Reject a devis and release associated order stock"""
        devis = self.db.query(Document).filter(
            and_(
                Document.id == devis_id,
                Document.type == DocumentType.DEVIS
            )
        ).first()
        
        if not devis:
            raise ValueError("Devis not found")
            
        if devis.status not in [DocumentStatus.EN_ATTENTE, DocumentStatus.BROUILLON]:
            raise ValueError(f"Cannot reject devis in status {devis.status.value}")
            
        old_status = devis.status
        devis.status = DocumentStatus.REFUSE
        
        # Release stock if order exists (Audit Point B.4)
        if devis.order_id:
            from app.services.order_service import OrderService
            order_service = OrderService(self.db)
            try:
                # We reuse reject_order logic to release stock and update order status
                print(f"📉 Rejecting associated order {devis.order_id} for devis {devis.document_number}")
                order_service.reject_order(devis.order_id, reason=f"Devis rejected: {reason}", user_id=user_id)
            except Exception as e:
                print(f"⚠️ Failed to auto-reject order: {e}")
                
        # History
        history = DocumentHistory(
            document_id=devis.id,
            changed_by=user_id,
            action="rejected",
            description=f"Devis rejected. Reason: {reason}",
            old_value=old_status.value,
            new_value=DocumentStatus.REFUSE.value
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
            
        # Check devis expiration (Audit Point B.3)
        if devis.valid_until and devis.valid_until < datetime.now(timezone.utc):
            raise ValueError(f"Devis expired on {devis.valid_until}. Cannot convert to facture.")
        
        # Create facture from devis
        facture = Document(
            type=DocumentType.FACTURE,
            document_number=self.generate_document_number(DocumentType.FACTURE),
            status=DocumentStatus.EN_ATTENTE,
            client_id=devis.client_id,
            order_id=devis.order_id,
            issue_date=datetime.now(timezone.utc),
            due_date=devis.due_date,
            subtotal=float(devis.subtotal or 0),
            tax_amount=float(devis.tax_amount or 0),
            discount=float(devis.discount or 0),
            shipping_fee=float(devis.shipping_fee or 0),
            total_amount=float(devis.total_amount or 0),
            payment_status=PaymentStatus.NON_PAYE,
            paid_amount=0.0,
            remaining_amount=float(devis.total_amount or 0),
            notes=devis.notes,
            terms=devis.terms,
            reference_document_id=devis.id,
            version=1,
            is_latest_version=True,
            
            # Facture specific
            payment_terms=PaymentTerms.IMMEDIATE, # Default
            payment_deadline=devis.due_date # Default deadline
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
                quantity=int(devis_item.quantity or 0),
                unit_price=float(devis_item.unit_price or 0),
                discount_percent=float(devis_item.discount_percent or 0),
                tax_percent=float(devis_item.tax_percent or 0),
                subtotal=float(devis_item.subtotal or 0)
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
                    # LOCKING: Use with_for_update to prevent race conditions during stock deduction
                    product = self.db.query(Product).with_for_update().filter(Product.id == item.product_id).first()
                    if product:
                        req_qty = int(item.quantity or 0)
                        available_stock = int(product.stock_quantity or 0)
                        
                        # Check stock availability first (Critical Audit Point A.4)
                        if available_stock < req_qty:
                            raise ValueError(f"Stock insuffisant pour {product.name} (Requis: {req_qty}, Réel: {available_stock})")

                        # Reduce both actual stock and reserved quantity
                        product.stock_quantity = available_stock - req_qty
                        product.reserved_quantity = max(0, int(product.reserved_quantity or 0) - req_qty)
                        
                        # Create inventory movement
                        movement = InventoryMovement(
                            product_id=product.id,
                            movement_type=MovementType.STOCK_OUT,
                            quantity=req_qty,
                            previous_stock=available_stock,
                            new_stock=product.stock_quantity,
                            reference_type="facture",
                            reference_id=facture.id,
                            reason="sale",
                            notes=f"Stock sold via facture {facture.document_number}",
                            performed_by=user_id
                        )
                        self.db.add(movement)
                        
                        # Check if stock deduction triggers any alerts
                        from app.services.stock_alert_service import StockAlertService
                        alert_service = StockAlertService(self.db)
                        alert_service.check_and_create_alerts()
                
                order.stock_reserved = False
                
                # Ensure Order Status is CONFIRMED (if not already)
                from app.models.order import OrderStatus
                if order.status != OrderStatus.CONFIRMED:
                     order.status = OrderStatus.CONFIRMED
                     # We can add history here if strictly needed, but it might be redundant if already confirmed by accept_devis
        
        # Send admin notification
        try:
            from app.services.admin_notification_service import AdminNotificationService
            notification_service = AdminNotificationService(self.db)
            notification_service.notify_facture_created(
                facture_number=facture.document_number,
                devis_number=devis.document_number,
                total_amount=float(facture.total_amount),
                facture_id=facture.id,
                user_id=user_id
            )
        except Exception as e:
            print(f"Failed to send facture admin notification: {e}")
            
        # Send Client Email Notification
        try:
            from app.services.notification_service import NotificationService
            client_notification = NotificationService()
            client_name = devis.client.company_name if devis.client.type == "b2b" else f"{devis.client.first_name} {devis.client.last_name}"
            
            client_notification.notify_facture_created(
                {
                    "id": str(facture.id),
                    "document_number": facture.document_number,
                    "issue_date": facture.issue_date,
                    "total_amount": float(facture.total_amount),
                    "due_date": facture.due_date
                },
                devis.client.email,
                client_name
            )
        except Exception as e:
            print(f"Failed to send facture client email: {e}")
            
        self.db.commit()
        self.db.refresh(facture)
        return facture
    
    def create_avoir_from_facture(
        self, 
        avoir_data: AvoirFromFacture, 
        user_id: Optional[UUID] = None
    ) -> Document:
        """Create an avoir (credit note) from a facture with selected products"""
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
        
        # VALIDATION: Ensure items are provided for product selection
        if not avoir_data.items or len(avoir_data.items) == 0:
            raise ValueError("Vous devez sélectionner au moins un produit pour créer un avoir")
        
        # VALIDATION: Verify all selected products exist in the facture
        facture_product_ids = {str(item.product_id) for item in facture.items}
        for item_data in avoir_data.items:
            if str(item_data.product_id) not in facture_product_ids:
                raise ValueError(f"Le produit {item_data.product_id} n'existe pas dans la facture")
        
        # VALIDATION: Check returned quantities don't exceed facture quantities
        for item_data in avoir_data.items:
            facture_item = next((item for item in facture.items if item.product_id == item_data.product_id), None)
            if facture_item and item_data.quantity > facture_item.quantity:
                raise ValueError(f"La quantité retournée ({item_data.quantity}) dépasse la quantité facturée ({facture_item.quantity}) pour le produit {facture_item.product_name}")
        
        # Calculate avoir total based on selected items
        avoir_total = float(sum(
            float(item.quantity) * float(item.unit_price) * (1 - float(item.discount_percent) / 100)
            for item in avoir_data.items
        ))
        
        if avoir_total <= 0:
            raise ValueError("Le montant de l'avoir doit être supérieur à 0")
        
        # VALIDATION: Check if avoir total exceeds facture total
        existing_avoirs_total = float(sum(float(d.total_amount) for d in facture.related_documents if d.type == DocumentType.AVOIR))
        if existing_avoirs_total + avoir_total > float(facture.total_amount):
            raise ValueError(f"Impossible de créer un avoir de {avoir_total} DT. Total des avoirs ({existing_avoirs_total + avoir_total}) dépasserait le montant de la facture ({facture.total_amount}).")
        
        # Create avoir
        avoir = Document(
            type=DocumentType.AVOIR,
            document_number=self.generate_document_number(DocumentType.AVOIR),
            status=DocumentStatus.EN_ATTENTE,
            client_id=facture.client_id,
            order_id=facture.order_id,
            issue_date=datetime.now(timezone.utc),
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
            is_latest_version=True,
            avoir_reason=avoir_data.reason
        )
        self.db.add(avoir)
        self.db.flush()
        
        # Create avoir items and return stock ONLY for selected products
        returned_items_count = 0
        for item_data in avoir_data.items:
            product = self.db.query(Product).filter(Product.id == item_data.product_id).first()
            
            avoir_item = DocumentItem(
                document_id=avoir.id,
                product_id=item_data.product_id,
                product_name=product.name if product else "Unknown",
                product_sku=product.sku if product else "",
                quantity=item_data.quantity,
                unit_price=float(item_data.unit_price),
                discount_percent=float(item_data.discount_percent),
                tax_percent=float(item_data.tax_percent),
                subtotal=float(item_data.quantity) * float(item_data.unit_price) * (1 - float(item_data.discount_percent) / 100)
            )
            self.db.add(avoir_item)
            
            # Return stock ONLY for selected products
            if product:
                product.stock_quantity += item_data.quantity
                returned_items_count += 1
                
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
                
                # Check if this resolves any stock alerts
                from app.services.stock_alert_service import StockAlertService
                alert_service = StockAlertService(self.db)
                alert_service.check_and_create_alerts()
        
        # Update facture payment status if avoir affects it
        if avoir_total >= float(facture.remaining_amount):
            facture.payment_status = PaymentStatus.PAYE
            facture.remaining_amount = 0.0
        else:
            facture.remaining_amount = float(facture.remaining_amount) - avoir_total
        
        # Create histories
        avoir_history = DocumentHistory(
            document_id=avoir.id,
            changed_by=user_id,
            action="created_from_facture",
            description=f"Avoir created from facture {facture.document_number}. Reason: {avoir_data.reason}. {returned_items_count} product(s) returned to stock.",
            new_value=json.dumps({"total_amount": avoir_total, "items_returned": returned_items_count})
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
        
        # Send admin notification
        try:
            from app.services.admin_notification_service import AdminNotificationService
            notification_service = AdminNotificationService(self.db)
            notification_service.notify_avoir_created(
                avoir_number=avoir.document_number,
                facture_number=facture.document_number,
                total_amount=avoir_total,
                returned_items_count=returned_items_count,
                avoir_id=avoir.id,
                user_id=user_id
            )
        except Exception as e:
            print(f"Failed to send avoir notification: {e}")
        
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
        
        if payment_data.amount > float(document.remaining_amount):
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
        document.paid_amount = float(document.paid_amount) + float(payment_data.amount)
        document.remaining_amount = float(document.remaining_amount) - float(payment_data.amount)
        
        if document.remaining_amount == 0:
            document.payment_status = PaymentStatus.PAYE
            document.status = DocumentStatus.PAYE
            
            # Sync with parent Order
            if document.order_id:
                from app.models.order import Order, OrderStatus, OrderHistory
                order = self.db.query(Order).filter(Order.id == document.order_id).first()
                if order and order.status != OrderStatus.COMPLETED:
                    print(f"🔄 Facture paid - updating order {order.order_number} to COMPLETED")
                    old_order_status = order.status
                    order.status = OrderStatus.COMPLETED
                    
                    # Add order history
                    order_history = OrderHistory(
                        order_id=order.id,
                        changed_by=user_id,
                        action="status_changed",
                        old_value=old_order_status.value,
                        new_value=OrderStatus.COMPLETED.value,
                        notes=f"Order completed automatically after full payment of Facture {document.document_number}"
                    )
                    self.db.add(order_history)
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
        
        # Send notification
        try:
            from app.services.notification_service import NotificationService
            from app.models.client import Client  # Import Client if not available on Document relationship directly
            
            # Need to get client info. Document might have client relationship loaded or we fetch it
            client = self.db.query(Client).filter(Client.id == document.client_id).first()
            if client:
                notification_service = NotificationService()
                client_name = client.company_name if client.type == "b2b" else f"{client.first_name} {client.last_name}"
                
                notification_service.notify_payment_received(
                    {
                        "id": str(payment.id),
                        "amount": float(payment.amount),
                        "payment_method": payment.payment_method.value,
                        "payment_date": payment.payment_date
                    },
                    {
                        "id": str(document.id),
                        "document_number": document.document_number,
                        "remaining_amount": float(document.remaining_amount)
                    },
                    client.email,
                    client_name
                )
        except Exception as e:
            print(f"Failed to send payment receipt email: {e}")
            
        return payment
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
    
    def get_devis_by_order(
        self,
        order_id: UUID,
        include_versions: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Document], int]:
        """
        Get all devis for a specific order with pagination.
        Returns (devis_list, total_count)
        """
        # Base query
        query = self.db.query(Document).filter(
            and_(
                Document.order_id == order_id,
                Document.type == DocumentType.DEVIS
            )
        ).options(
            joinedload(Document.items),
            joinedload(Document.client),
            joinedload(Document.history).joinedload(DocumentHistory.user)
        )
        
        # Filter by latest version if not including all versions
        if not include_versions:
            query = query.filter(Document.is_latest_version == True)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        devis_list = query.order_by(desc(Document.created_at)).offset(skip).limit(limit).all()
        
        return devis_list, total
    
    def get_facture_source_devis(self, facture_id: UUID) -> Optional[Document]:
        """
        Get the source devis that was converted to this facture.
        Returns the latest version of the devis by default.
        """
        facture = self.db.query(Document).filter(
            and_(
                Document.id == facture_id,
                Document.type == DocumentType.FACTURE
            )
        ).first()
        
        if not facture or not facture.reference_document_id:
            return None
        
        # Get the devis that this facture was created from
        devis = self.db.query(Document).options(
            joinedload(Document.items),
            joinedload(Document.client),
            joinedload(Document.history).joinedload(DocumentHistory.user)
        ).filter(
            Document.id == facture.reference_document_id
        ).first()
        
        return devis
    
    def get_devis_timeline(self, order_id: UUID) -> List[Dict[str, Any]]:
        """
        Get timeline of all devis events for an order.
        Returns a chronological list of all devis-related events.
        """
        # Get all devis for this order (all versions)
        all_devis = self.db.query(Document).filter(
            and_(
                Document.order_id == order_id,
                Document.type == DocumentType.DEVIS
            )
        ).options(
            joinedload(Document.history).joinedload(DocumentHistory.user)
        ).order_by(Document.created_at).all()
        
        timeline_events = []
        
        for devis in all_devis:
            # Add all history events for this devis
            for history in devis.history:
                event = {
                    "event_type": history.action,
                    "devis_id": str(devis.id),
                    "devis_number": devis.document_number,
                    "version": devis.version,
                    "timestamp": history.created_at.isoformat() if history.created_at else None,
                    "changed_by": str(history.changed_by) if history.changed_by else None,
                    "changed_by_name": f"{history.user.first_name} {history.user.last_name}" if history.user else None,
                    "description": history.description,
                    "total_amount": float(devis.total_amount) if devis.total_amount else None,
                    "status": devis.status.value,
                    "action_details": {
                        "old_value": history.old_value,
                        "new_value": history.new_value
                    }
                }
                timeline_events.append(event)
        
        # Sort all events by timestamp
        timeline_events.sort(key=lambda x: x["timestamp"])
        
        return timeline_events
