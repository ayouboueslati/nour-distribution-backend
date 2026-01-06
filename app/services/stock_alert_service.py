from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc, func

from app.models.stock_alert import StockAlert, AlertType, AlertPriority
from app.models.product import Product
from app.services.base import BaseService


class StockAlertService(BaseService[StockAlert]):
    def __init__(self, db: Session):
        super().__init__(StockAlert, db)
    
    def check_and_create_alerts(self) -> List[StockAlert]:
        """
        Scan all products and create alerts for stock issues.
        Returns list of newly created alerts.
        """
        new_alerts = []
        
        # Get all active products
        products = self.db.query(Product).filter(Product.is_active == True).all()
        
        for product in products:
            # Check for out of stock
            if product.stock_quantity <= 0:
                alert = self._create_or_update_alert(
                    product=product,
                    alert_type=AlertType.OUT_OF_STOCK,
                    priority=AlertPriority.CRITICAL,
                    message=f"Product '{product.name}' is out of stock",
                    threshold_value=0,
                    current_value=product.stock_quantity
                )
                if alert:
                    new_alerts.append(alert)
            
            # Check for low stock
            elif product.available_quantity <= product.min_stock_level:
                priority = AlertPriority.HIGH if product.available_quantity <= (product.min_stock_level / 2) else AlertPriority.MEDIUM
                alert = self._create_or_update_alert(
                    product=product,
                    alert_type=AlertType.LOW_STOCK,
                    priority=priority,
                    message=f"Product '{product.name}' is running low (Available: {product.available_quantity}, Min: {product.min_stock_level})",
                    threshold_value=product.min_stock_level,
                    current_value=product.available_quantity
                )
                if alert:
                    new_alerts.append(alert)
            
            # Check for overstock (if max_stock_level is set)
            elif product.max_stock_level and product.stock_quantity > product.max_stock_level:
                alert = self._create_or_update_alert(
                    product=product,
                    alert_type=AlertType.OVERSTOCK,
                    priority=AlertPriority.LOW,
                    message=f"Product '{product.name}' is overstocked (Current: {product.stock_quantity}, Max: {product.max_stock_level})",
                    threshold_value=product.max_stock_level,
                    current_value=product.stock_quantity
                )
                if alert:
                    new_alerts.append(alert)
            else:
                # Resolve any existing active alerts for this product if stock is normal
                self._resolve_product_alerts(product.id)
        
        self.db.commit()
        return new_alerts
    
    def _create_or_update_alert(
        self,
        product: Product,
        alert_type: AlertType,
        priority: AlertPriority,
        message: str,
        threshold_value: Optional[int],
        current_value: int
    ) -> Optional[StockAlert]:
        """
        Create a new alert or update existing one if already exists.
        Returns the alert if newly created, None if updated.
        """
        # Check if similar active alert already exists
        existing_alert = self.db.query(StockAlert).filter(
            and_(
                StockAlert.product_id == product.id,
                StockAlert.alert_type == alert_type,
                StockAlert.is_active == True
            )
        ).first()
        
        if existing_alert:
            # Update existing alert
            existing_alert.priority = priority
            existing_alert.message = message
            existing_alert.current_value = current_value
            existing_alert.threshold_value = threshold_value
            existing_alert.updated_at = datetime.now(timezone.utc)
            return None
        else:
            # Create new alert
            new_alert = StockAlert(
                product_id=product.id,
                alert_type=alert_type,
                priority=priority,
                message=message,
                threshold_value=threshold_value,
                current_value=current_value,
                is_active=True
            )
            self.db.add(new_alert)
            return new_alert
    
    def _resolve_product_alerts(self, product_id: UUID) -> None:
        """Mark all active alerts for a product as resolved."""
        active_alerts = self.db.query(StockAlert).filter(
            and_(
                StockAlert.product_id == product_id,
                StockAlert.is_active == True
            )
        ).all()
        
        for alert in active_alerts:
            alert.is_active = False
            alert.resolved_at = datetime.now(timezone.utc)
    
    def get_active_alerts(
        self,
        priority: Optional[AlertPriority] = None,
        alert_type: Optional[AlertType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[StockAlert]:
        """Get active alerts with optional filtering."""
        query = self.db.query(StockAlert).options(
            joinedload(StockAlert.product)
        ).filter(StockAlert.is_active == True)
        
        if priority:
            query = query.filter(StockAlert.priority == priority)
        
        if alert_type:
            query = query.filter(StockAlert.alert_type == alert_type)
        
        return query.order_by(
            desc(StockAlert.priority),
            desc(StockAlert.created_at)
        ).offset(skip).limit(limit).all()
    
    def get_alerts_by_priority(self) -> Dict[str, List[StockAlert]]:
        """Get active alerts grouped by priority."""
        active_alerts = self.get_active_alerts(limit=1000)
        
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for alert in active_alerts:
            grouped[alert.priority.value].append(alert)
        
        return grouped
    
    def acknowledge_alert(self, alert_id: UUID, user_id: UUID) -> StockAlert:
        """Mark an alert as acknowledged."""
        alert = self.get_by_id(alert_id)
        if not alert:
            raise ValueError("Alert not found")
        
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id
        alert.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def resolve_alert(self, alert_id: UUID) -> StockAlert:
        """Mark an alert as resolved."""
        alert = self.get_by_id(alert_id)
        if not alert:
            raise ValueError("Alert not found")
        
        alert.is_active = False
        alert.resolved_at = datetime.now(timezone.utc)
        alert.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get_alert_history(
        self,
        product_id: Optional[UUID] = None,
        days: int = 30,
        skip: int = 0,
        limit: int = 100
    ) -> List[StockAlert]:
        """Get alert history with optional product filter."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = self.db.query(StockAlert).options(
            joinedload(StockAlert.product)
        ).filter(StockAlert.created_at >= cutoff_date)
        
        if product_id:
            query = query.filter(StockAlert.product_id == product_id)
        
        return query.order_by(desc(StockAlert.created_at)).offset(skip).limit(limit).all()
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary statistics of active alerts."""
        active_alerts = self.get_active_alerts(limit=1000)
        
        summary = {
            "total_active": len(active_alerts),
            "by_priority": {
                "critical": len([a for a in active_alerts if a.priority == AlertPriority.CRITICAL]),
                "high": len([a for a in active_alerts if a.priority == AlertPriority.HIGH]),
                "medium": len([a for a in active_alerts if a.priority == AlertPriority.MEDIUM]),
                "low": len([a for a in active_alerts if a.priority == AlertPriority.LOW])
            },
            "by_type": {
                "out_of_stock": len([a for a in active_alerts if a.alert_type == AlertType.OUT_OF_STOCK]),
                "low_stock": len([a for a in active_alerts if a.alert_type == AlertType.LOW_STOCK]),
                "overstock": len([a for a in active_alerts if a.alert_type == AlertType.OVERSTOCK]),
                "expiring_reservation": len([a for a in active_alerts if a.alert_type == AlertType.EXPIRING_RESERVATION]),
                "stock_discrepancy": len([a for a in active_alerts if a.alert_type == AlertType.STOCK_DISCREPANCY])
            },
            "acknowledged": len([a for a in active_alerts if a.acknowledged_at is not None]),
            "unacknowledged": len([a for a in active_alerts if a.acknowledged_at is None])
        }
        
        return summary
