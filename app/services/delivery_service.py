from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc

from app.models.delivery import DeliveryNote, DeliveryNoteItem, DeliveryStatus
from app.models.order import Order, OrderStatus, OrderItem
from app.models.document import Document, DocumentType
from app.services.base import BaseService

class DeliveryService(BaseService[DeliveryNote]):
    def __init__(self, db: Session):
        super().__init__(DeliveryNote, db)
        
    def generate_delivery_number(self) -> str:
        """Generate unique delivery note number"""
        now = datetime.now(timezone.utc)
        prefix = f"BL-{now.strftime('%Y%m%d')}"
        
        last_doc = self.db.query(DeliveryNote).filter(
            DeliveryNote.delivery_number.like(f"{prefix}%")
        ).order_by(desc(DeliveryNote.delivery_number)).first()
        
        if last_doc:
            last_num = int(last_doc.delivery_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
            
        return f"{prefix}-{new_num:04d}"

    def create_delivery_note(
        self, 
        order_id: UUID, 
        items: List[Dict[str, Any]], 
        user_id: Optional[UUID] = None,
        notes: str = None
    ) -> DeliveryNote:
        """
        Create a delivery note for an order.
        Supports partial delivery.
        items: [{"product_id": UUID, "quantity": int}]
        """
        order = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
            
        if order.status not in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING]:
            # Technically can deliver if confirmed
            raise ValueError("Order must be CONFIRMED to create delivery note")
            
        # Create Note
        note = DeliveryNote(
            delivery_number=self.generate_delivery_number(),
            status=DeliveryStatus.PENDING,
            order_id=order.id,
            client_id=order.client_id,
            shipping_address=order.shipping_address,
            notes=notes
        )
        self.db.add(note)
        self.db.flush()
        
        # Add Items
        for item_data in items:
            product_id = item_data["product_id"]
            quantity = item_data["quantity"]
            
            # Verify order item exists and check quantity
            order_item = next((i for i in order.items if str(i.product_id) == str(product_id)), None)
            if not order_item:
                raise ValueError(f"Product {product_id} not in order")
            
            # TODO: Check if quantity exceeds ordered quantity minus already delivered
            # For now, just create
            
            note_item = DeliveryNoteItem(
                delivery_note_id=note.id,
                product_id=product_id,
                product_name=order_item.product.name if order_item.product else "Unknown",
                product_sku=order_item.product.sku if order_item.product else "",
                quantity=quantity
            )
            self.db.add(note_item)
            
        self.db.commit()
        self.db.refresh(note)
        return note

    def mark_as_shipped(self, delivery_id: UUID, carrier: str = None, tracking: str = None) -> DeliveryNote:
        note = self.get(delivery_id)
        if not note:
            raise ValueError("Delivery note not found")
            
        note.status = DeliveryStatus.SHIPPED
        note.shipped_at = datetime.now(timezone.utc)
        if carrier: note.carrier_name = carrier
        if tracking: note.tracking_reference = tracking
        
        # Update Order Status
        if note.order and note.order.status != OrderStatus.SHIPPED:
             note.order.status = OrderStatus.SHIPPED
             
        self.db.commit()
        return note

    def mark_as_delivered(self, delivery_id: UUID) -> DeliveryNote:
        note = self.get(delivery_id)
        if not note:
            raise ValueError("Delivery note not found")
            
        note.status = DeliveryStatus.DELIVERED
        note.delivered_at = datetime.now(timezone.utc)
        
        # Update Order Status
        if note.order:
             # Check if all items delivered? Simpler for now: just mark DELIVERED
             note.order.status = OrderStatus.DELIVERED
             
        self.db.commit()
        return note
