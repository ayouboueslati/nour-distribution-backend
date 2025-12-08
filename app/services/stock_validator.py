from typing import Dict, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.product import Product
from app.models.cart import CartItem
from app.models.order import Order

class StockValidator:
    """Real-time stock validation service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_cart_stock(self, cart_items: List[CartItem]) -> Dict[str, any]:
        """Validate stock for all cart items in real-time"""
        validation_results = {
            "is_valid": True,
            "items": [],
            "out_of_stock": [],
            "low_stock_warnings": []
        }
        
        for cart_item in cart_items:
            product = cart_item.product
            
            # Calculate real-time available stock
            available_stock = product.stock_quantity - product.reserved_quantity
            
            if cart_item.quantity > available_stock:
                validation_results["is_valid"] = False
                validation_results["out_of_stock"].append({
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "requested": cart_item.quantity,
                    "available": available_stock
                })
            elif available_stock <= product.min_stock_level:
                validation_results["low_stock_warnings"].append({
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "available": available_stock,
                    "min_stock": product.min_stock_level
                })
            
            validation_results["items"].append({
                "product_id": str(product.id),
                "product_name": product.name,
                "quantity": cart_item.quantity,
                "available": available_stock,
                "is_available": cart_item.quantity <= available_stock
            })
        
        return validation_results
    
    def get_real_time_stock(self, product_id: UUID) -> Dict[str, any]:
        """Get real-time stock with reservations"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            return None
        
        # Calculate pending reservations
        pending_reservations = self.db.query(func.sum(CartItem.quantity)).filter(
            CartItem.product_id == product_id,
            CartItem.reserved_at.isnot(None),
            CartItem.reservation_expires_at > datetime.utcnow()
        ).scalar() or 0
        
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "physical_stock": product.stock_quantity,
            "reserved_stock": product.reserved_quantity,
            "pending_reservations": pending_reservations,
            "available_stock": product.stock_quantity - product.reserved_quantity,
            "min_stock_level": product.min_stock_level,
            "needs_restock": product.stock_quantity <= product.min_stock_level,
            "last_updated": product.updated_at
        }
    
    def reserve_stock_in_transaction(self, product_id: UUID, quantity: int, timeout: int = 30) -> bool:
        """Atomic stock reservation with optimistic locking"""
        from sqlalchemy import text
        
        # Use PostgreSQL advisory lock for concurrent safety
        lock_key = hash(f"product_{product_id}") % 2**31
        
        try:
            # Get advisory lock
            self.db.execute(text(f"SELECT pg_advisory_lock({lock_key})"))
            
            product = self.db.query(Product).filter(Product.id == product_id).with_for_update().first()
            
            if not product:
                return False
            
            available = product.stock_quantity - product.reserved_quantity
            
            if quantity > available:
                return False
            
            # Reserve stock
            product.reserved_quantity += quantity
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e
        finally:
            # Release advisory lock
            self.db.execute(text(f"SELECT pg_advisory_unlock({lock_key})"))