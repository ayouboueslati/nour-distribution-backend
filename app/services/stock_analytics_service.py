from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, func

from app.models.product import Product
from app.models.inventory import InventoryMovement, MovementType
from app.models.category import Category
from app.services.base import BaseService


class StockAnalyticsService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_stock_overview(self) -> Dict[str, Any]:
        """Get comprehensive stock overview metrics."""
        products = self.db.query(Product).filter(Product.is_active == True).all()
        
        total_products = len(products)
        total_stock_value = sum(
            float(p.stock_quantity or 0) * float(p.cost_price or 0)
            for p in products
        )
        total_stock_quantity = sum(p.stock_quantity or 0 for p in products)
        total_reserved = sum(p.reserved_quantity or 0 for p in products)
        total_available = sum(p.available_quantity for p in products)
        
        low_stock_count = len([p for p in products if p.needs_restock])
        out_of_stock_count = len([p for p in products if p.stock_quantity <= 0])
        
        return {
            "total_products": total_products,
            "total_stock_value": round(total_stock_value, 2),
            "total_stock_quantity": total_stock_quantity,
            "total_reserved": total_reserved,
            "total_available": total_available,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "stock_health_percentage": round(
                ((total_products - out_of_stock_count - low_stock_count) / total_products * 100) if total_products > 0 else 0,
                2
            )
        }
    
    def get_stock_value_by_category(self) -> List[Dict[str, Any]]:
        """Get stock value breakdown by category."""
        categories = self.db.query(Category).all()
        
        category_data = []
        for category in categories:
            products = self.db.query(Product).filter(
                and_(
                    Product.category_id == category.id,
                    Product.is_active == True
                )
            ).all()
            
            total_value = sum(
                float(p.stock_quantity or 0) * float(p.cost_price or 0)
                for p in products
            )
            total_quantity = sum(p.stock_quantity or 0 for p in products)
            
            category_data.append({
                "category_id": str(category.id),
                "category_name": category.name,
                "product_count": len(products),
                "total_stock_value": round(total_value, 2),
                "total_quantity": total_quantity
            })
        
        return sorted(category_data, key=lambda x: x["total_stock_value"], reverse=True)
    
    def get_stock_movements_trend(self, days: int = 30) -> Dict[str, Any]:
        """Get stock movement trends over specified period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        movements = self.db.query(InventoryMovement).filter(
            InventoryMovement.created_at >= cutoff_date
        ).all()
        
        # Group by movement type
        stock_in = [m for m in movements if m.movement_type == MovementType.STOCK_IN]
        stock_out = [m for m in movements if m.movement_type == MovementType.STOCK_OUT]
        reserved = [m for m in movements if m.movement_type == MovementType.RESERVED]
        released = [m for m in movements if m.movement_type == MovementType.RELEASED]
        
        return {
            "period_days": days,
            "total_movements": len(movements),
            "stock_in": {
                "count": len(stock_in),
                "total_quantity": sum(m.quantity for m in stock_in)
            },
            "stock_out": {
                "count": len(stock_out),
                "total_quantity": sum(m.quantity for m in stock_out)
            },
            "reserved": {
                "count": len(reserved),
                "total_quantity": sum(m.quantity for m in reserved)
            },
            "released": {
                "count": len(released),
                "total_quantity": sum(m.quantity for m in released)
            },
            "net_change": sum(m.quantity for m in stock_in) - sum(m.quantity for m in stock_out)
        }
    
    def get_stock_turnover_analysis(self, days: int = 30) -> List[Dict[str, Any]]:
        """Calculate stock turnover rate for each product."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        products = self.db.query(Product).filter(Product.is_active == True).all()
        
        turnover_data = []
        for product in products:
            # Get stock out movements (sales) in the period
            stock_out_movements = self.db.query(InventoryMovement).filter(
                and_(
                    InventoryMovement.product_id == product.id,
                    InventoryMovement.movement_type == MovementType.STOCK_OUT,
                    InventoryMovement.created_at >= cutoff_date
                )
            ).all()
            
            total_sold = sum(m.quantity for m in stock_out_movements)
            avg_stock = product.stock_quantity  # Simplified - could calculate average over period
            
            # Turnover rate = (units sold / average stock) * 100
            turnover_rate = (total_sold / avg_stock * 100) if avg_stock > 0 else 0
            
            # Classify movement speed
            if turnover_rate > 50:
                movement_speed = "fast"
            elif turnover_rate > 20:
                movement_speed = "moderate"
            elif turnover_rate > 0:
                movement_speed = "slow"
            else:
                movement_speed = "stagnant"
            
            turnover_data.append({
                "product_id": str(product.id),
                "product_name": product.name,
                "sku": product.sku,
                "current_stock": product.stock_quantity,
                "units_sold": total_sold,
                "turnover_rate": round(turnover_rate, 2),
                "movement_speed": movement_speed,
                "days_to_stockout": round((product.stock_quantity / (total_sold / days)) if total_sold > 0 else 999, 1)
            })
        
        return sorted(turnover_data, key=lambda x: x["turnover_rate"], reverse=True)
    
    def get_fast_moving_products(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """Get top fast-moving products."""
        turnover_data = self.get_stock_turnover_analysis(days=days)
        return turnover_data[:limit]
    
    def get_slow_moving_products(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """Get slow-moving products that need attention."""
        turnover_data = self.get_stock_turnover_analysis(days=days)
        slow_moving = [p for p in turnover_data if p["movement_speed"] in ["slow", "stagnant"]]
        return slow_moving[:limit]
    
    def get_stock_aging_report(self) -> List[Dict[str, Any]]:
        """Analyze stock aging based on last movement."""
        products = self.db.query(Product).filter(Product.is_active == True).all()
        
        aging_data = []
        for product in products:
            # Get last stock movement
            last_movement = self.db.query(InventoryMovement).filter(
                InventoryMovement.product_id == product.id
            ).order_by(desc(InventoryMovement.created_at)).first()
            
            if last_movement:
                days_since_movement = (datetime.now(timezone.utc) - last_movement.created_at).days
            else:
                days_since_movement = 999  # No movement recorded
            
            # Classify aging
            if days_since_movement > 90:
                aging_category = "very_old"
            elif days_since_movement > 60:
                aging_category = "old"
            elif days_since_movement > 30:
                aging_category = "moderate"
            else:
                aging_category = "fresh"
            
            aging_data.append({
                "product_id": str(product.id),
                "product_name": product.name,
                "sku": product.sku,
                "current_stock": product.stock_quantity,
                "stock_value": round(float(product.stock_quantity or 0) * float(product.cost_price or 0), 2),
                "days_since_last_movement": days_since_movement,
                "last_movement_date": last_movement.created_at.isoformat() if last_movement else None,
                "aging_category": aging_category
            })
        
        return sorted(aging_data, key=lambda x: x["days_since_last_movement"], reverse=True)
    
    def get_stock_forecast(self, product_id: UUID, days_ahead: int = 30) -> Dict[str, Any]:
        """Forecast when a product will run out of stock."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
        
        # Get average daily sales over last 30 days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        stock_out_movements = self.db.query(InventoryMovement).filter(
            and_(
                InventoryMovement.product_id == product_id,
                InventoryMovement.movement_type == MovementType.STOCK_OUT,
                InventoryMovement.created_at >= cutoff_date
            )
        ).all()
        
        total_sold = sum(m.quantity for m in stock_out_movements)
        avg_daily_sales = total_sold / 30 if total_sold > 0 else 0
        
        # Calculate days until stockout
        if avg_daily_sales > 0:
            days_until_stockout = product.available_quantity / avg_daily_sales
        else:
            days_until_stockout = 999  # No sales, can't predict
        
        # Forecast stock levels
        forecast_dates = []
        for day in range(0, days_ahead + 1, 5):  # Every 5 days
            forecasted_stock = max(0, product.available_quantity - (avg_daily_sales * day))
            forecast_dates.append({
                "days_from_now": day,
                "date": (datetime.now(timezone.utc) + timedelta(days=day)).date().isoformat(),
                "forecasted_stock": round(forecasted_stock, 0)
            })
        
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "current_stock": product.stock_quantity,
            "available_stock": product.available_quantity,
            "avg_daily_sales": round(avg_daily_sales, 2),
            "days_until_stockout": round(days_until_stockout, 1) if days_until_stockout < 999 else None,
            "stockout_date": (datetime.now(timezone.utc) + timedelta(days=days_until_stockout)).date().isoformat() if days_until_stockout < 999 else None,
            "forecast": forecast_dates,
            "recommendation": self._get_restock_recommendation(days_until_stockout, product.min_stock_level)
        }
    
    def _get_restock_recommendation(self, days_until_stockout: float, min_stock_level: int) -> str:
        """Get restock recommendation based on forecast."""
        if days_until_stockout < 7:
            return "URGENT: Restock immediately"
        elif days_until_stockout < 14:
            return "HIGH PRIORITY: Restock within 1 week"
        elif days_until_stockout < 30:
            return "MEDIUM PRIORITY: Restock within 2 weeks"
        else:
            return "LOW PRIORITY: Stock levels are healthy"
