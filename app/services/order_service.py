from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
import json

from app.models.order import Order, OrderItem, OrderHistory, OrderStatus
from app.models.product import Product
from app.models.client import Client
from app.models.cart import Cart, CartItem
from app.models.inventory import InventoryMovement, MovementType
from app.schemas.order import OrderCreate, OrderUpdate, OrderPricing, OrderFromCart
from app.services.base import BaseService

class OrderService(BaseService[Order]):
    def __init__(self, db: Session):
        super().__init__(Order, db)
    
    def generate_order_number(self) -> str:
        """Generate unique order number"""
        from datetime import datetime
        now = datetime.now()
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
    
    def create_order_from_cart(self, cart_id: UUID, order_data: OrderFromCart, user_id: Optional[UUID] = None) -> Order:
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
        client = self.db.query(Client).filter(Client.id == cart.client_id).first()
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
            client_id=cart.client_id,
            status=OrderStatus.EN_ATTENTE,
            submitted_at=datetime.utcnow(),
            shipping_address=order_data.shipping_address,
            delivery_notes=order_data.delivery_notes,
            stock_reserved=False,
            reservation_expires_at=datetime.utcnow() + timedelta(days=30)
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
            new_value=json.dumps({"status": OrderStatus.EN_ATTENTE.value}),
            notes="Order created from cart"
        )
        self.db.add(history)
        
        # Deactivate cart
        cart.is_active = False
        
        self.db.commit()
        self.db.refresh(order)
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
            status=OrderStatus.EN_ATTENTE,
            submitted_at=datetime.utcnow(),
            shipping_address=order_data.shipping_address,
            delivery_notes=order_data.delivery_notes,
            stock_reserved=False,
            reservation_expires_at=datetime.utcnow() + timedelta(days=30)
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
            new_value=json.dumps({"status": OrderStatus.EN_ATTENTE.value}),
            notes="Order created directly"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def update_order_pricing(self, order_id: UUID, pricing_data: OrderPricing, user_id: Optional[UUID] = None) -> Order:
        """Admin sets pricing for order"""
        order = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status not in [OrderStatus.EN_ATTENTE, OrderStatus.EN_TRAITEMENT]:
            raise ValueError("Cannot update pricing for this order status")
        
        # Update order items with pricing
        for item_update in pricing_data.items:
            order_item = next((item for item in order.items if item.id == item_update.id), None)
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
        order.processed_at = datetime.utcnow()
        order.status = OrderStatus.EN_TRAITEMENT
        
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
    
    def confirm_order(self, order_id: UUID, user_id: Optional[UUID] = None) -> Order:
        """Admin confirms order"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status != OrderStatus.EN_TRAITEMENT:
            raise ValueError("Order must be in processing status to confirm")
        
        old_status = order.status
        order.status = OrderStatus.CONFIRME
        order.confirmed_at = datetime.utcnow()
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="status_changed",
            old_value=old_status.value,
            new_value=OrderStatus.CONFIRME.value,
            notes="Order confirmed by admin"
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def cancel_order(self, order_id: UUID, reason: str, user_id: Optional[UUID] = None) -> Order:
        """Cancel order and release reserved stock"""
        order = self.db.query(Order).options(
            joinedload(Order.items)
        ).filter(Order.id == order_id).first()
        
        if not order:
            raise ValueError("Order not found")
        
        if order.status == OrderStatus.ANNULE:
            raise ValueError("Order already cancelled")
        
        old_status = order.status
        
        # Release reserved stock
        if order.stock_reserved:
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
                        reason="order_cancelled",
                        notes=f"Stock released from cancelled order {order.order_number}",
                        performed_by=user_id
                    )
                    self.db.add(movement)
            
            order.stock_reserved = False
        
        order.status = OrderStatus.ANNULE
        
        # Create history
        history = OrderHistory(
            order_id=order.id,
            changed_by=user_id,
            action="cancelled",
            old_value=old_status.value,
            new_value=OrderStatus.ANNULE.value,
            notes=reason
        )
        self.db.add(history)
        
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def get_order_with_details(self, order_id: UUID) -> Optional[Order]:
        """Get order with all related data"""
        return self.db.query(Order).options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.client),
            joinedload(Order.history)
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
    
    def check_expired_reservations(self) -> List[UUID]:
        """Check and release expired order reservations"""
        now = datetime.utcnow()
        
        expired_orders = self.db.query(Order).filter(
            and_(
                Order.status == OrderStatus.EN_ATTENTE,
                Order.reservation_expires_at < now,
                Order.stock_reserved == True
            )
        ).all()
        
        released_orders = []
        for order in expired_orders:
            self.cancel_order(
                order.id,
                "Automatic cancellation: Reservation expired after 30 days",
                user_id=None
            )
            released_orders.append(order.id)
        
        return released_orders