from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
import json

from app.models.order import Order, OrderItem, OrderHistory, OrderStatus
from app.models.product import Product
from app.models.client import Client
from app.models.cart import Cart, CartItem
from app.models.inventory import InventoryMovement, MovementType
from app.schemas.order import OrderCreate, OrderUpdate, OrderPricing, OrderFromCart, OrderItemUpdate, OrderItemCreate
from app.services.base import BaseService

class OrderService(BaseService[Order]):
    def __init__(self, db: Session):
        super().__init__(Order, db)
    
    def generate_order_number(self) -> str:
        """Generate unique order number"""
        from datetime import datetime
        now = datetime.now(timezone.utc)
        prefix = f"CMD-{now.strftime('%Y%m%d')}"
        
        # Get last order number for today
        last_order = self.db.query(Order).filter(
            Order.order_number.like(f"{prefix}%")
        ).order_by(desc(Order.order_number)).first()
        
        if last_order:
            last_num = int(last_order.order_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}-{new_num:04d}"
    
    def create_order_from_cart(self, cart_id: UUID, client_id: UUID, order_data: OrderFromCart, user_id: Optional[UUID] = None) -> Order:
        """Create order from cart and reserve stock"""
        # Get cart with items
        cart = self.db.query(Cart).options(
            joinedload(Cart.items).joinedload(CartItem.product)
        ).filter(Cart.id == cart_id).first()
        
        if not cart:
            raise ValueError("Cart not found")
        
        if not cart.items:
            raise ValueError("Cart is empty")
        
        # Verify client exists
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise ValueError("Client not found")
        
        # Check stock availability for all items
        for cart_item in cart.items:
            product = cart_item.product
            if cart_item.quantity > product.available_quantity:
                raise ValueError(f"Insufficient stock for {product.name}. Available: {product.available_quantity}")
        
        # Create order
        order = Order(
            order_number=self.generate_order_number(),
            client_id=client_id,
            status=OrderStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
            shipping_address=order_data.shipping_address,
            delivery_notes=order_data.delivery_notes,
            stock_reserved=False,
            reservation_expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        self.db.add(order)
        self.db.flush()
        
        # Create order items from cart
        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                unit_price=None,  # Will be set by admin
                discount_percent=0.0,
                subtotal=0.0
            )
            self.db.add(order_item)
        
        # Reserve stock
        for cart_item in cart.items:
            product = cart_item.product
            product.reserved_quantity += cart_item.quantity
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=product.id,
                movement_type=MovementType.RESERVED,
                quantity=cart_item.quantity,
                previous_stock=product.stock_quantity,
                new_stock=product.stock_quantity,
                reference_type="order",
                reference_id=order.id,
                reason="order_created",
                notes=f"Stock reserved for order {order.order_number}",
                performed_by=user_id
            )
            self.db.add(movement)
        
        order.stock_reserved = True
        
        # Create order history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="created",
            new_value=json.dumps({"status": OrderStatus.PENDING.value}),
            notes="Order created from cart"
        )
        self.db.add(history)
        
        # Deactivate cart
        cart.is_active = False
        
        self.db.commit()
        self.db.refresh(order)
        
        # Send notification
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            client_name = client.company_name if client.type == "b2b" else f"{client.first_name} {client.last_name}"
            notification_service.notify_order_submitted(
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "submitted_at": order.submitted_at,
                    "items": [{"quantity": item.quantity} for item in order.items]
                },
                client.email,
                client_name
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            
        return order
    
    def create_order_direct(self, order_data: OrderCreate, user_id: Optional[UUID] = None) -> Order:
        """Create order directly (without cart)"""
        # Verify client
        client = self.db.query(Client).filter(Client.id == order_data.client_id).first()
        if not client:
            raise ValueError("Client not found")
        
        # Verify all products and stock
        for item_data in order_data.items:
            product = self.db.query(Product).filter(
                and_(
                    Product.id == item_data.product_id,
                    Product.is_active == True
                )
            ).first()
            
            if not product:
                raise ValueError(f"Product {item_data.product_id} not found or inactive")
            
            if item_data.quantity > product.available_quantity:
                raise ValueError(f"Insufficient stock for {product.name}")
        
        # Create order
        order = Order(
            order_number=self.generate_order_number(),
            client_id=order_data.client_id,
            status=OrderStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
            shipping_address=order_data.shipping_address,
            delivery_notes=order_data.delivery_notes,
            stock_reserved=False,
            reservation_expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        self.db.add(order)
        self.db.flush()
        
        # Create order items and reserve stock
        for item_data in order_data.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=None,
                discount_percent=0.0,
                subtotal=0.0
            )
            self.db.add(order_item)
            
            # Reserve stock
            product = self.db.query(Product).filter(Product.id == item_data.product_id).first()
            product.reserved_quantity += item_data.quantity
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=product.id,
                movement_type=MovementType.RESERVED,
                quantity=item_data.quantity,
                previous_stock=product.stock_quantity,
                new_stock=product.stock_quantity,
                reference_type="order",
                reference_id=order.id,
                reason="order_created",
                notes=f"Stock reserved for order {order.order_number}",
                performed_by=user_id
            )
            self.db.add(movement)
        
        order.stock_reserved = True
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="created",
            new_value=json.dumps({"status": OrderStatus.PENDING.value}),
            notes="Order created directly"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        
        # Send notification
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            client_name = client.company_name if client.type == "b2b" else f"{client.first_name} {client.last_name}"
            notification_service.notify_order_submitted(
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "submitted_at": order.submitted_at,
                    "items": [{"quantity": item.quantity} for item in order.items]
                },
                client.email,
                client_name
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            
        return order
    
    def update_order_pricing(self, order_id: UUID, pricing_data: OrderPricing, user_id: Optional[UUID] = None) -> Order:
        """Admin sets pricing for order"""
        order = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            raise ValueError("Cannot update pricing for this order status")
        
        # Update order items with pricing
        for item_update in pricing_data.items:
            order_item = next((item for item in order.items if item.product_id == item_update.product_id), None)
            if order_item:
                if item_update.quantity is not None:
                    order_item.quantity = item_update.quantity
                if item_update.unit_price is not None:
                    order_item.unit_price = item_update.unit_price
                if item_update.discount_percent is not None:
                    order_item.discount_percent = item_update.discount_percent
                
                # Calculate subtotal
                base_price = item_update.unit_price * order_item.quantity
                discount_amount = base_price * (item_update.discount_percent / 100)
                order_item.subtotal = base_price - discount_amount
        
        # Update order totals
        old_values = {
            "subtotal": order.subtotal,
            "total_amount": order.total_amount
        }
        
        order.subtotal = pricing_data.subtotal
        order.shipping_fee = pricing_data.shipping_fee
        order.discount = pricing_data.discount
        order.tax_amount = pricing_data.tax_amount
        order.total_amount = pricing_data.total_amount
        order.processed_at = datetime.now(timezone.utc)
        order.status = OrderStatus.PROCESSING
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="pricing_updated",
            old_value=json.dumps(old_values),
            new_value=json.dumps({
                "subtotal": order.subtotal,
                "total_amount": order.total_amount
            }),
            notes="Admin updated pricing"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def _generate_devis(self, order: Order, user_id: Optional[UUID]) -> None:
        """Helper to generate devis from order with ALL information"""
        from app.services.document_service import DocumentService
        from app.schemas.document import DevisFromOrder
        from datetime import timedelta
    
        # Note: Multiple devis can be created for negotiation purposes
        # Each call to accept_order can create a new devis version
    
        # VALIDATION : Vérifier que la commande a des prix
        if not order.total_amount or order.total_amount == 0:
            error_msg = f"Impossible de générer un devis : la commande {order.order_number} n'a pas de prix défini"
            print(f"❌ {error_msg}")
        
            error_history = OrderHistory(
                order_id=order.id,
                changed_by=user_id,
                action="devis_generation_failed",
                notes=error_msg
            )
            self.db.add(error_history)
            self.db.commit()
            raise ValueError(error_msg)
    
        # Extract client name before the f-string to avoid nested f-string syntax
        # error on Python <3.12 (backslashes not allowed inside f-string expressions)
        if order.client.type == 'b2b':
            client_display_name = order.client.company_name
        else:
            client_display_name = f"{order.client.first_name} {order.client.last_name}"

        # Préparer les notes avec informations client
        client_info = f"""
Informations Client:
- Nom: {client_display_name}
- Email: {order.client.email}
- Téléphone: {order.client.phone or 'Non renseigné'}
- Adresse: {order.client.address or 'Non renseignée'}
- Type: {'Professionnel (B2B)' if order.client.type == 'b2b' else 'Particulier (B2C)'}

Adresse de livraison: {order.shipping_address or "Identique à l'adresse client"}
"""
    
        if order.delivery_notes:
            client_info += "\nNotes de livraison: " + order.delivery_notes
    
        document_service = DocumentService(self.db)
    
        # Calculer la date d'échéance (30 jours par défaut)
        issue_date = datetime.now(timezone.utc)
        due_date = issue_date + timedelta(days=30)
    
        devis_data = DevisFromOrder(
            order_id=order.id,
            issue_date=issue_date,
            due_date=due_date,
            notes=client_info,
            terms="""Conditions de paiement:
- Devis valable 30 jours
- Paiement à la commande ou selon accord
- TVA 19% incluse (Tunisie)
- Livraison sous 7-14 jours ouvrables

En acceptant ce devis, vous confirmez votre commande."""
        )
    
        try:
            print(f"📝 Generating devis for order {order.order_number}...")
            devis = document_service.create_devis_from_order(
                order.id, 
                devis_data, 
                user_id
            )
            
            print(f"✅ Devis {devis.document_number} created successfully!")
            
            # Ajouter l'historique de succès
            devis_history = OrderHistory(
                order_id=order.id,
                changed_by=user_id,
                action="devis_generated",
                new_value=json.dumps({
                    "devis_number": devis.document_number, 
                    "devis_id": str(devis.id),
                    "total_amount": float(devis.total_amount),
                    "client_name": order.client.company_name if order.client.type == 'b2b' else f"{order.client.first_name} {order.client.last_name}",
                    "client_email": order.client.email
                }),
                notes=f"Devis {devis.document_number} généré automatiquement avec succès"
            )
            self.db.add(devis_history)
            self.db.commit()
            
            # Send notification
            try:
                from app.services.notification_service import NotificationService
                notification_service = NotificationService()
                client_name = order.client.company_name if order.client.type == "b2b" else f"{order.client.first_name} {order.client.last_name}"
                
                # Pass latest devis ID for the link
                order_dict = {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "subtotal": order.subtotal,
                    "shipping_fee": order.shipping_fee,
                    "tax_amount": order.tax_amount,
                    "total_amount": order.total_amount,
                    "items": [{
                        "product_name": item.product.name, 
                        "quantity": item.quantity, 
                        "unit_price": float(item.unit_price or 0.0),
                        "subtotal": float(item.subtotal or 0.0)
                    } for item in order.items],
                    "latest_devis_id": str(devis.id)
                }
                
                # Send Order Processed / Devis Created email
                notification_service.notify_order_processed(
                    order_dict,
                    order.client.email,
                    client_name,
                    "Admin" # Could replace with actual admin name if user_id linked to User model
                )
            except Exception as e:
                print(f"Failed to send email: {e}")
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération du devis: {str(e)}"
            print(f"❌ {error_msg}")
            
            error_history = OrderHistory(
                order_id=order.id,
                changed_by=user_id,
                action="devis_generation_failed",
                notes=error_msg
            )
            self.db.add(error_history)
            self.db.commit()
            raise ValueError(error_msg)
    
    
    def accept_order(self, order_id: UUID, notes: Optional[str] = None, user_id: Optional[UUID] = None) -> Order:
        """Accept order - change status from PENDING to PROCESSING and auto-generate Devis"""
        order = self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.client)
        ).filter(Order.id == order_id).first()
    
        if not order:
            raise ValueError("Order not found")
    
        # B2B/B2C Auto-Pricing Logic
        # If order items have no price (0 or None), try to auto-fill from product
        prices_updated = False
        client_type = order.client.type if order.client else "b2c"
        
        for item in order.items:
            if not item.unit_price or item.unit_price == 0:
                product = item.product
                if product:
                    # Auto-select price logic
                    if client_type == "b2b":
                        item.unit_price = product.wholesale_price if product.wholesale_price and product.wholesale_price > 0 else product.retail_price
                    else:
                        item.unit_price = product.retail_price
                    prices_updated = True
        
        if prices_updated:
            # Recalculate totals if we auto-filled prices
            subtotal = sum((item.unit_price or 0) * item.quantity for item in order.items)
            # Apply standard tax (19% TVA - hardcoded for now)
            total_tax = subtotal * 0.19 
            order.total_amount = subtotal + total_tax
            self.db.commit()
            self.db.refresh(order)

        # Final Verification: Ensure prices are set now
        if not order.total_amount or order.total_amount == 0:
             raise ValueError("La commande doit avoir des prix définis. Impossible d'auto-définir les prix (produits sans prix de base).")
        
        for item in order.items:
             if not item.unit_price or item.unit_price == 0:
                 raise ValueError(f"Le produit '{item.product.name}' n'a pas de prix défini et pas de prix par défaut.")
    
        # Allow PROCESSING status (idempotent), but ensure Devis is checked
        if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            raise ValueError(f"Impossible d'accepter une commande avec le statut : {order.status.value}")
    
        # Store old status before any changes
        old_status = order.status
        
        # Changer le statut si nécessaire
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.PROCESSING
            order.processed_at = datetime.now(timezone.utc)
        
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="accepted",
            old_value=json.dumps({"status": old_status.value}),
            new_value=json.dumps({"status": OrderStatus.PROCESSING.value}),
            notes=notes or "Commande acceptée par l'administrateur"
        )
        self.db.add(history)
        self.db.flush()

        # Générer le Devis automatiquement avec TOUTES les informations
        self._generate_devis(order, user_id)
    
        self.db.commit()
        self.db.refresh(order)
        
        # Send notification (Order Processed / Devis Created happens in _generate_devis, but we can notify acceptance here if needed)
        # Note: _generate_devis handles its own notifications usually, but let's check
        
        return order
    
    def confirm_order(self, order_id: UUID, user_id: Optional[UUID] = None) -> Order:
        """Admin confirms order (without auto-generating devis, use accept_order for that)"""
        order = self.db.query(Order).options(joinedload(Order.client)).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status != OrderStatus.PROCESSING:
            raise ValueError("Order must be in processing status to confirm")
        
        old_status = order.status
        order.status = OrderStatus.CONFIRMED
        order.confirmed_at = datetime.now(timezone.utc)
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="status_changed",
            old_value=old_status.value,
            new_value=OrderStatus.CONFIRMED.value,
            notes="Order confirmed by admin"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        
        # Send notification
        try:
            from app.services.notification_service import NotificationService
            notification_service = NotificationService()
            client_name = order.client.company_name if order.client.type == "b2b" else f"{order.client.first_name} {order.client.last_name}"
            notification_service.notify_order_confirmed(
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "confirmed_at": order.confirmed_at,
                    "total_amount": order.total_amount
                },
                order.client.email,
                client_name
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            
        return order
    
    def cancel_order(self, order_id: UUID, reason: str, user_id: Optional[UUID] = None) -> Order:
        """Cancel order and release reserved stock"""
        order = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status == OrderStatus.CANCELLED:
            raise ValueError("Order already cancelled")
        
        old_status = order.status
        
        # Release reserved stock
        if order.stock_reserved:
            self._release_order_stock(order, user_id, reason="order_cancelled")
        
        order.status = OrderStatus.CANCELLED
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="cancelled",
            old_value=old_status.value,
            new_value=OrderStatus.CANCELLED.value,
            notes=reason
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order

    def reject_order(self, order_id: UUID, reason: str, user_id: Optional[UUID] = None) -> Order:
        """Reject order (admin action) and release reserved stock"""
        order = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
            
        if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
             raise ValueError(f"Cannot reject order with status {order.status.value}")
             
        old_status = order.status
        
        # Release reserved stock
        if order.stock_reserved:
            self._release_order_stock(order, user_id, reason="order_rejected")
            
        order.status = OrderStatus.REJECTED
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="rejected",
            old_value=old_status.value,
            new_value=OrderStatus.REJECTED.value,
            notes=reason
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel_expired_reservations(self, expiry_threshold_hours: int = 72) -> int:
        """
        New method to find and cancel orders with expired reservations.
        Returns count of cancelled orders.
        Default: 72 hours (3 days)
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=expiry_threshold_hours)
        
        # Find pending orders created before cutoff that still have stock reserved
        expired_orders = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(
            and_(
                Order.status == OrderStatus.PENDING,
                Order.stock_reserved == True,
                Order.submitted_at < cutoff_time
            )
        ).all()
        
        count = 0
        for order in expired_orders:
            try:
                print(f"⏳ Use 'cancel_order' for expired order {order.order_number}")
                # We use cancel_order reuse logic
                # System user UUID could be passed here if available, else None implies System
                self.cancel_order(
                    order.id, 
                    reason=f"Auto-cancelled: Reservation expired (> {expiry_threshold_hours}h)", 
                    user_id=None
                )
                count += 1
            except Exception as e:
                print(f"❌ Failed to auto-cancel order {order.order_number}: {e}")
                
        return count

    def _release_order_stock(self, order: Order, user_id: Optional[UUID], reason: str):
        """Helper to release stock for an entire order"""
        for item in order.items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.reserved_quantity = max(0, product.reserved_quantity - item.quantity)
                
                # Create inventory movement
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type=MovementType.RELEASED,
                    quantity=item.quantity,
                    previous_stock=product.stock_quantity,
                    new_stock=product.stock_quantity,
                    reference_type="order",
                    reference_id=order.id,
                    reason=reason,
                    notes=f"Stock released from {reason} order {order.order_number}",
                    performed_by=user_id
                )
                self.db.add(movement)
        
        order.stock_reserved = False
    
    def get_order_with_details(self, order_id: UUID) -> Optional[Order]:
        """Get order with all related data"""
        return self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.client),
            joinedload(Order.history),
            joinedload(Order.documents)
        ).filter(Order.id == order_id).first()
    
    def get_orders_by_status(self, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get orders filtered by status"""
        return self.db.query(Order).filter(
            Order.status == status
        ).order_by(desc(Order.created_at)).offset(skip).limit(limit).all()
    
    def get_client_orders(self, client_id: UUID, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders for a client"""
        return self.db.query(Order).filter(
            Order.client_id == client_id
        ).order_by(desc(Order.created_at)).offset(skip).limit(limit).all()
    
    

    
    def update_order_item(self, order_id: UUID, item_id: UUID, item_data: OrderItemUpdate, user_id: Optional[UUID] = None) -> Order:
        """Update single order item - change quantity or price. Only allowed for PENDING or PROCESSING orders"""
        order = self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            raise ValueError(f"Cannot edit order with status {order.status.value}")
            
        # Find item
        order_item = next((item for item in order.items if item.product_id == item_id or item.id == item_id), None)
        if not order_item:
            # Try to look it up directly if not found in preloaded items (should not happen if ID is correct)
            raise ValueError("Order item not found")

        product = order_item.product
        
        # Check stock if quantity increases
        if item_data.quantity is not None and item_data.quantity > order_item.quantity:
            additional_qty = item_data.quantity - order_item.quantity
            # Check availability (considering we already reserved some)
            if product.stock_quantity < additional_qty:
                raise ValueError(f"Insufficient stock for {product.name}")
            
            # Update reservation
            product.reserved_quantity += additional_qty
            
            # Inventory movement for additional reservation
            movement = InventoryMovement(
                product_id=product.id,
                movement_type=MovementType.RESERVED,
                quantity=additional_qty,
                previous_stock=product.stock_quantity,
                new_stock=product.stock_quantity,
                reference_type="order",
                reference_id=order.id,
                reason="order_update",
                notes=f"Additional stock reserved for order {order.order_number}",
                performed_by=user_id
            )
            self.db.add(movement)
            
        elif item_data.quantity is not None and item_data.quantity < order_item.quantity:
            # Release some stock
            released_qty = order_item.quantity - item_data.quantity
            product.reserved_quantity = max(0, product.reserved_quantity - released_qty)
            
            # Inventory movement for released reservation
            movement = InventoryMovement(
                product_id=product.id,
                movement_type=MovementType.RELEASED,
                quantity=released_qty,
                previous_stock=product.stock_quantity,
                new_stock=product.stock_quantity,
                reference_type="order",
                reference_id=order.id,
                reason="order_update",
                notes=f"Stock released from order update {order.order_number}",
                performed_by=user_id
            )
            self.db.add(movement)

        # Update item fields
        if item_data.quantity is not None:
            order_item.quantity = item_data.quantity
            
        if item_data.unit_price is not None:
            order_item.unit_price = item_data.unit_price
            
        if item_data.discount_percent is not None:
            order_item.discount_percent = item_data.discount_percent
            
        # Recalculate subtotal
        price_to_use = float(order_item.unit_price if order_item.unit_price is not None else (product.retail_price or 0))
        base_price = price_to_use * order_item.quantity
        discount_amount = base_price * (order_item.discount_percent / 100)
        order_item.subtotal = base_price - discount_amount
        
        # Recalculate order totals
        order.subtotal = float(sum(item.subtotal for item in order.items))
        order.total_amount = order.subtotal + float(order.shipping_fee or 0) - float(order.discount or 0) + float(order.tax_amount or 0)
        
        # Add history entry
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="item_updated",
            new_value=json.dumps({"product_id": str(order_item.product_id), "quantity": order_item.quantity}),
            notes=f"Order item updated: {product.name}"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order
    
    
    def add_order_item(self, order_id: UUID, item_data: OrderItemCreate, user_id: Optional[UUID] = None) -> Order:
        """Add item to order (or update quantity if exists). Only for PENDING/PROCESSING orders."""
        order = self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
            
        if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            raise ValueError(f"Cannot edit order with status {order.status.value}")
            
        # Check if product exists and is active
        product = self.db.query(Product).filter(
            and_(
                Product.id == item_data.product_id,
                Product.is_active == True
            )
        ).first()
        
        if not product:
            raise ValueError(f"Product {item_data.product_id} not found or inactive")
            
        # Check if item already exists in order
        existing_item = next((item for item in order.items if item.product_id == item_data.product_id), None)
        
        if existing_item:
            # Update existing item
            return self.update_order_item(
                order_id, 
                existing_item.id, 
                OrderItemUpdate(
                    product_id=existing_item.product_id,
                    quantity=existing_item.quantity + item_data.quantity,
                    discount_percent=existing_item.discount_percent
                ),
                user_id
            )
            
        # Check stock availability
        if item_data.quantity > product.available_quantity:
            raise ValueError(f"Insufficient stock for {product.name}. Available: {product.available_quantity}")
            
        # Reserve stock
        product.reserved_quantity += item_data.quantity
        
        # Create inventory movement
        movement = InventoryMovement(
            product_id=product.id,
            movement_type=MovementType.RESERVED,
            quantity=item_data.quantity,
            previous_stock=product.stock_quantity,
            new_stock=product.stock_quantity,
            reference_type="order",
            reference_id=order.id,
            reason="order_add_item",
            notes=f"Stock reserved for new item in order {order.order_number}",
            performed_by=user_id
        )
        self.db.add(movement)
        
        # key error fix: ensure order.stock_reserved is true if we are adding items
        if not order.stock_reserved:
            order.stock_reserved = True
            
        # Create new order item
        # Calculate price and subtotal
        price_to_use = float(product.retail_price or 0)
        base_price = price_to_use * item_data.quantity
        discount_amount = base_price * (item_data.discount_percent / 100)
        subtotal = base_price - discount_amount
        
        new_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item_data.quantity,
            unit_price=price_to_use,
            discount_percent=item_data.discount_percent,
            subtotal=subtotal
        )
        self.db.add(new_item)
        
        # Update order totals (need to flush first to get new_item in order.items if re-querying, 
        # but here we can just add to current totals or re-calculate)
        # Safest is to add to session, flush, and re-calculate
        self.db.flush()
        
        # Recalculate order totals
        # We need to refresh order.items to include the new one
        self.db.refresh(order)
        
        order.subtotal = float(sum(item.subtotal for item in order.items))
        order.total_amount = order.subtotal + float(order.shipping_fee or 0) - float(order.discount or 0) + float(order.tax_amount or 0)
        
        # History
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="item_added",
            new_value=json.dumps({"product_id": str(product.id), "quantity": item_data.quantity}),
            notes=f"Added item: {product.name}"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order

    def remove_order_item(self, order_id: UUID, item_id: UUID, user_id: Optional[UUID] = None) -> Order:
        """Remove item from order and release stock"""
        order = self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
            
        if order.status not in [OrderStatus.PENDING, OrderStatus.PROCESSING]:
            raise ValueError(f"Cannot edit order with status {order.status.value}")
            
        # Find item
        order_item = next((item for item in order.items if item.product_id == item_id or item.id == item_id), None)
        if not order_item:
            raise ValueError("Order item not found")
            
        product = order_item.product
        quantity_to_release = order_item.quantity
        
        # Release stock
        product.reserved_quantity = max(0, product.reserved_quantity - quantity_to_release)
        
        # Inventory movement
        movement = InventoryMovement(
            product_id=product.id,
            movement_type=MovementType.RELEASED,
            quantity=quantity_to_release,
            previous_stock=product.stock_quantity,
            new_stock=product.stock_quantity,
            reference_type="order",
            reference_id=order.id,
            reason="order_remove_item",
            notes=f"Stock released from removed item in order {order.order_number}",
            performed_by=user_id
        )
        self.db.add(movement)
        
        # Remove item
        self.db.delete(order_item)
        self.db.flush()
        self.db.refresh(order)
        
        # Recalculate totals
        order.subtotal = sum(item.subtotal for item in order.items)
        order.total_amount = order.subtotal + order.shipping_fee - order.discount + order.tax_amount
        
        # History
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="item_removed",
            old_value=json.dumps({"product_id": str(product.id), "quantity": quantity_to_release}),
            notes=f"Removed item: {product.name}"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order

