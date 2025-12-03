from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.models.inventory import InventoryMovement, MovementType
from app.models.product import Product
from app.schemas.inventory import InventoryMovementCreate
from app.services.base import BaseService

class InventoryService(BaseService[InventoryMovement]):
    def __init__(self, db: Session):
        super().__init__(InventoryMovement, db)

    def create_movement(self, movement_data: InventoryMovementCreate, user_id: Optional[UUID] = None) -> InventoryMovement:
        """Create a new inventory movement"""
        # Verify product exists
        product = self.db.query(Product).filter(Product.id == movement_data.product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Get current stock for the product
        current_stock = product.stock_quantity
        
        # Calculate new stock based on movement type
        if movement_data.movement_type == MovementType.STOCK_IN:
            new_stock = current_stock + movement_data.quantity
        elif movement_data.movement_type == MovementType.STOCK_OUT:
            new_stock = current_stock - movement_data.quantity
        elif movement_data.movement_type == MovementType.RESERVED:
            new_stock = current_stock  # Stock doesn't change for reservations
        elif movement_data.movement_type == MovementType.RELEASED:
            new_stock = current_stock  # Stock doesn't change for releases
        else:
            new_stock = current_stock

        # Update product stock if it's a physical movement
        if movement_data.movement_type in [MovementType.STOCK_IN, MovementType.STOCK_OUT]:
            product.stock_quantity = new_stock

        # Create movement record
        movement_dict = movement_data.dict()
        movement_dict.update({
            'previous_stock': current_stock,
            'new_stock': new_stock,
            'performed_by': user_id
        })

        movement = self.create(movement_dict)
        
        # Commit both changes
        self.db.commit()
        self.db.refresh(movement)
        
        return movement

    def get_product_movements(self, product_id: UUID, limit: int = 50) -> List[InventoryMovement]:
        """Get inventory movements for a specific product"""
        return self.db.query(InventoryMovement).filter(
            InventoryMovement.product_id == product_id
        ).order_by(desc(InventoryMovement.created_at)).limit(limit).all()

    def get_stock_level_report(self) -> List[Dict[str, Any]]:
        """Get comprehensive stock level report"""
        return self.db.query(
            Product.id,
            Product.name,
            Product.sku,
            Product.stock_quantity,
            Product.reserved_quantity,
            Product.min_stock_level,
            Product.max_stock_level,
            (Product.stock_quantity - Product.reserved_quantity).label('available_quantity'),
            (Product.stock_quantity <= Product.min_stock_level).label('needs_restock'),
            func.coalesce(
                func.max(InventoryMovement.created_at), 
                Product.created_at
            ).label('last_movement')
        ).outerjoin(InventoryMovement).group_by(Product.id).all()

    def get_low_stock_alerts(self) -> List[Dict[str, Any]]:
        """Get products that need immediate restocking"""
        low_stock_products = self.db.query(Product).filter(
            and_(
                Product.is_active == True,
                Product.stock_quantity <= Product.min_stock_level
            )
        ).all()

        alerts = []
        for product in low_stock_products:
            needed_quantity = product.min_stock_level * 2 - product.stock_quantity  # Restock to 2x min level
            
            # Determine urgency
            if product.stock_quantity == 0:
                urgency = "critical"
            elif product.stock_quantity <= product.min_stock_level * 0.5:
                urgency = "high"
            else:
                urgency = "medium"

            alerts.append({
                'product_id': product.id,
                'product_name': product.name,
                'product_sku': product.sku,
                'current_stock': product.stock_quantity,
                'min_stock_level': product.min_stock_level,
                'needed_quantity': max(needed_quantity, 1),
                'urgency': urgency
            })

        return alerts

    def get_inventory_turnover(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get inventory turnover analysis for the last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        turnover_data = self.db.query(
            Product.id,
            Product.name,
            Product.sku,
            Product.stock_quantity,
            func.sum(
                func.case(
                    (InventoryMovement.movement_type == MovementType.STOCK_OUT, InventoryMovement.quantity),
                    else_=0
                )
            ).label('sold_quantity')
        ).outerjoin(
            InventoryMovement, 
            and_(
                InventoryMovement.product_id == Product.id,
                InventoryMovement.created_at >= start_date
            )
        ).group_by(Product.id).all()

        result = []
        for product_id, name, sku, stock_quantity, sold_quantity in turnover_data:
            sold_quantity = sold_quantity or 0
            turnover_rate = (sold_quantity / stock_quantity) * 100 if stock_quantity > 0 else 0
            
            result.append({
                'product_id': product_id,
                'product_name': name,
                'product_sku': sku,
                'current_stock': stock_quantity,
                'sold_quantity': sold_quantity,
                'turnover_rate': round(turnover_rate, 2),
                'days_of_supply': (stock_quantity / (sold_quantity / days)) if sold_quantity > 0 else float('inf')
            })

        return result