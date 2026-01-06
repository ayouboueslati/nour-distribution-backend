from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.client import Client
from app.models.inventory import InventoryMovement, MovementType
from app.schemas.cart import CartItemCreate, CartItemUpdate
from app.services.base import BaseService

class CartService(BaseService[Cart]):
    def __init__(self, db: Session):
        super().__init__(Cart, db)
    
    def get_or_create_cart(self, guest_session_id: UUID) -> Cart:
        """Get active cart for guest - NO CLIENT REQUIRED"""
        # Try to find cart by guest_session_id first
        cart = self.db.query(Cart).filter(
            and_(
                Cart.guest_session_id == str(guest_session_id),
                Cart.is_active == True
            )
        ).first()
    
        if not cart:
            # Create new cart without client
            cart = Cart(
                guest_session_id=str(guest_session_id),
                is_active=True
            )
            self.db.add(cart)
            self.db.commit()
            self.db.refresh(cart)
    
        return cart
    
    def add_item_to_cart(self, guest_session_id: UUID, item_data: CartItemCreate) -> CartItem:
        """Add item to guest cart - NO CLIENT CHECK"""
        print(f"CART SERVICE: Adding item - guest_session_id: {guest_session_id}, product_id: {item_data.product_id}, quantity: {item_data.quantity}")
    
        cart = self.get_or_create_cart(guest_session_id)
    
        print(f"CART SERVICE: Cart ID: {cart.id}, Guest Session: {cart.guest_session_id}")
    
        # Check product exists and is active
        product = self.db.query(Product).filter(
            and_(
                Product.id == item_data.product_id,
                Product.is_active == True
            )
        ).first()
    
        if not product:
            raise ValueError(f"Product with ID {item_data.product_id} not found or inactive")
    
        # Check stock availability
        available_stock = product.stock_quantity - product.reserved_quantity
        print(f"CART SERVICE: Available stock: {available_stock}, Requested: {item_data.quantity}")
    
        # Check if item already in cart
        existing_item = self.db.query(CartItem).filter(
            and_(
                CartItem.cart_id == cart.id,
                CartItem.product_id == item_data.product_id
            )
        ).first()
    
        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + item_data.quantity
        
            if new_quantity > available_stock:
                raise ValueError(f"Out of stock. Available: {available_stock}, Requested: {new_quantity}")
        
            existing_item.quantity = new_quantity
            self.db.commit()
            self.db.refresh(existing_item)
            return existing_item
        else:
            # Check stock for new item
            if item_data.quantity > available_stock:
                raise ValueError(f"Out of stock. Available: {available_stock}, Requested: {item_data.quantity}")
        
            # Create new cart item
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity
            )
            self.db.add(cart_item)
            self.db.commit()
            self.db.refresh(cart_item)
            return cart_item
    
    def update_cart_item(self, guest_session_id: UUID, item_id: UUID, update_data: CartItemUpdate) -> CartItem:
        """Update cart item quantity"""
        cart = self.get_or_create_cart(guest_session_id)
        
        cart_item = self.db.query(CartItem).filter(
            and_(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id
            )
        ).first()
        
        if not cart_item:
            raise ValueError("Cart item not found")
        
        # Check stock availability
        product = self.db.query(Product).filter(Product.id == cart_item.product_id).first()
        available_stock = product.available_quantity
        
        if update_data.quantity > available_stock:
            raise ValueError(f"Out of stock. Available: {available_stock}, Requested: {update_data.quantity}")
        
        cart_item.quantity = update_data.quantity
        self.db.commit()
        self.db.refresh(cart_item)
        return cart_item
    
    def remove_cart_item(self, guest_session_id: UUID, item_id: UUID) -> bool:
        """Remove item from cart"""
        cart = self.get_or_create_cart(guest_session_id)
        
        cart_item = self.db.query(CartItem).filter(
            and_(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id
            )
        ).first()
        
        if not cart_item:
            return False
        
        self.db.delete(cart_item)
        self.db.commit()
        return True
    
    def get_cart_with_details(self, guest_session_id: UUID) -> Optional[Cart]:
        """Get cart with all items and product details"""
        cart = self.db.query(Cart).options(
            joinedload(Cart.items).joinedload(CartItem.product)
        ).filter(
            and_(
                Cart.guest_session_id == str(guest_session_id),
                Cart.is_active == True
            )
        ).first()
        
        return cart
    
    def clear_cart(self, guest_session_id: UUID) -> bool:
        """Clear all items from cart"""
        cart = self.get_or_create_cart(guest_session_id)
        
        self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        self.db.commit()
        return True
    
    def reserve_cart_stock(self, cart_id: UUID) -> bool:
        """Reserve stock for cart items (temporary, 30 days)"""
        cart = self.db.query(Cart).options(
            joinedload(Cart.items).joinedload(CartItem.product)
        ).filter(Cart.id == cart_id).first()
        
        if not cart:
            raise ValueError("Cart not found")
        
        now = datetime.now(timezone.utc)
        expiration = now + timedelta(days=30)
        
        # Check all items have sufficient stock first
        for item in cart.items:
            product = item.product
            if item.quantity > product.available_quantity:
                raise ValueError(f"Insufficient stock for {product.name}")
        
        # Reserve stock
        for item in cart.items:
            product = item.product
            product.reserved_quantity += item.quantity
            
            # Update cart item reservation
            item.reserved_at = now
            item.reservation_expires_at = expiration
            
            # Create inventory movement
            movement = InventoryMovement(
                product_id=product.id,
                movement_type=MovementType.RESERVED,
                quantity=item.quantity,
                previous_stock=product.stock_quantity,
                new_stock=product.stock_quantity,
                reference_type="cart",
                reference_id=cart_id,
                reason="cart_checkout",
                notes=f"Stock reserved for cart {cart_id}"
            )
            self.db.add(movement)
        
        self.db.commit()
        return True
    
    def release_cart_stock(self, cart_id: UUID) -> bool:
        """Release reserved stock from cart"""
        cart = self.db.query(Cart).options(
            joinedload(Cart.items).joinedload(CartItem.product)
        ).filter(Cart.id == cart_id).first()
        
        if not cart:
            return False
        
        for item in cart.items:
            if item.reserved_at:
                product = item.product
                product.reserved_quantity = max(0, product.reserved_quantity - item.quantity)
                
                # Create inventory movement
                movement = InventoryMovement(
                    product_id=product.id,
                    movement_type=MovementType.RELEASED,
                    quantity=item.quantity,
                    previous_stock=product.stock_quantity,
                    new_stock=product.stock_quantity,
                    reference_type="cart",
                    reference_id=cart_id,
                    reason="cart_cancelled",
                    notes=f"Stock released from cart {cart_id}"
                )
                self.db.add(movement)
                
                # Clear reservation
                item.reserved_at = None
                item.reservation_expires_at = None
        
        self.db.commit()
        return True
    
    def release_expired_reservations(self) -> int:
        """
        Check and release expired cart reservations.
        Returns count of carts released.
        """
        now = datetime.now(timezone.utc)
        
        expired_items = self.db.query(CartItem).filter(
            and_(
                CartItem.reservation_expires_at.isnot(None),
                CartItem.reservation_expires_at < now
            )
        ).all()
        
        released_cart_ids = set()
        for item in expired_items:
            released_cart_ids.add(item.cart_id)
            
        count = 0
        for cart_id in released_cart_ids:
            if self.release_cart_stock(cart_id):
                count += 1
                
        return count