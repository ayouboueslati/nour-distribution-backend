from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager, require_admin
from app.models.user import User
from app.schemas.inventory import InventoryMovementCreate, InventoryMovementResponse
from app.schemas.inventory_adjustment import StockAdjustmentRequest
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService

router = APIRouter()

@router.post("/adjust", response_model=InventoryMovementResponse)
def adjust_stock(
    adjustment: StockAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manually adjust stock for a product.
    """
    service = InventoryService(db)
    try:
        movement = service.adjust_stock(
            product_id=adjustment.product_id,
            real_quantity=adjustment.real_quantity,
            reason=adjustment.reason,
            user_id=current_user.id
        )
        if not movement:
            raise HTTPException(status_code=400, detail="No stock change required (same quantity)")
        return movement
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/movements")
async def get_inventory_movements(
    product_id: Optional[UUID] = Query(None, description="Filter by product"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get inventory movements with filtering - Manager+ only
    """
    inventory_service = InventoryService(db)
    
    try:
        if product_id:
            movements = inventory_service.get_product_movements(product_id, limit=limit)
            # Apply pagination manually
            movements = movements[skip:skip + limit]
        else:
            movements = inventory_service.get_all(skip=skip, limit=limit)
        
        total = inventory_service.get_total_count()
        
        return {
            "movements": movements,
            "total": total,
            "page": skip // limit + 1,
            "page_size": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving inventory movements: {str(e)}"
        )

@router.get("/movements/{movement_id}")
async def get_inventory_movement(
    movement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get specific inventory movement - Manager+ only
    """
    inventory_service = InventoryService(db)
    
    movement = inventory_service.get_by_id(movement_id)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory movement not found"
        )
    
    return movement

@router.post("/movements")
async def create_inventory_movement(
    movement_data: InventoryMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create new inventory movement - Manager+ only
    """
    inventory_service = InventoryService(db)
    
    try:
        movement = inventory_service.create_movement(
            movement_data, 
            user_id=current_user.id
        )
        return movement
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating inventory movement: {str(e)}"
        )

@router.get("/stock-level-report")
async def get_stock_level_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get comprehensive stock level report - Manager+ only
    """
    inventory_service = InventoryService(db)
    
    try:
        stock_report = inventory_service.get_stock_level_report()
        return {"stock_report": stock_report}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating stock level report: {str(e)}"
        )

@router.get("/low-stock-alerts")
async def get_low_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get low stock alerts - Manager+ only
    """
    inventory_service = InventoryService(db)
    
    try:
        low_stock_alerts = inventory_service.get_low_stock_alerts()
        
        # Categorize by urgency
        critical_alerts = [alert for alert in low_stock_alerts if alert['urgency'] == 'critical']
        high_alerts = [alert for alert in low_stock_alerts if alert['urgency'] == 'high']
        medium_alerts = [alert for alert in low_stock_alerts if alert['urgency'] == 'medium']
        
        return {
            "alerts": low_stock_alerts,
            "summary": {
                "total": len(low_stock_alerts),
                "critical": len(critical_alerts),
                "high": len(high_alerts),
                "medium": len(medium_alerts)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving low stock alerts: {str(e)}"
        )

@router.get("/turnover-analysis")
async def get_inventory_turnover(
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get inventory turnover analysis - Manager+ only
    """
    inventory_service = InventoryService(db)
    
    try:
        turnover_data = inventory_service.get_inventory_turnover(days=days)
        
        # Calculate summary statistics
        total_products = len(turnover_data)
        fast_moving = [item for item in turnover_data if item['turnover_rate'] > 50]
        slow_moving = [item for item in turnover_data if item['turnover_rate'] < 10]
        
        return {
            "turnover_data": turnover_data,
            "summary": {
                "total_products": total_products,
                "analysis_period_days": days,
                "fast_moving_products": len(fast_moving),
                "slow_moving_products": len(slow_moving),
                "average_turnover_rate": sum(item['turnover_rate'] for item in turnover_data) / total_products if total_products > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating turnover analysis: {str(e)}"
        )

@router.get("/products/{product_id}/movements")
async def get_product_inventory_history(
    product_id: UUID,
    limit: int = Query(50, ge=1, le=500, description="Number of movements to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get inventory history for a specific product - Manager+ only
    """
    inventory_service = InventoryService(db)
    product_service = ProductService(db)
    
    # Verify product exists
    product = product_service.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    try:
        movements = inventory_service.get_product_movements(product_id, limit=limit)
        
        return {
            "product": {
                "id": product.id,
                "name": product.name,
                "sku": product.sku,
                "current_stock": product.stock_quantity,
                "available_quantity": product.available_quantity
            },
            "movements": movements,
            "total_movements": len(movements)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving product inventory history: {str(e)}"
        )


# Stock Alerts Endpoints
@router.get("/alerts")
async def get_stock_alerts(
    priority: Optional[str] = Query(None, description="Filter by priority: low, medium, high, critical"),
    alert_type: Optional[str] = Query(None, description="Filter by type: low_stock, out_of_stock, overstock"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get active stock alerts - Admin+ only
    """
    from app.services.stock_alert_service import StockAlertService
    from app.models.stock_alert import AlertPriority, AlertType
    
    alert_service = StockAlertService(db)
    
    try:
        # Convert string parameters to enums if provided
        priority_enum = AlertPriority(priority) if priority else None
        type_enum = AlertType(alert_type) if alert_type else None
        
        alerts = alert_service.get_active_alerts(
            priority=priority_enum,
            alert_type=type_enum,
            skip=skip,
            limit=limit
        )
        
        summary = alert_service.get_alert_summary()
        
        return {
            "alerts": alerts,
            "summary": summary,
            "total": len(alerts),
            "page": skip // limit + 1,
            "page_size": limit
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stock alerts: {str(e)}"
        )


@router.post("/alerts/check")
async def check_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Manually trigger stock alert check - Admin+ only
    """
    from app.services.stock_alert_service import StockAlertService
    
    alert_service = StockAlertService(db)
    
    try:
        new_alerts = alert_service.check_and_create_alerts()
        return {
            "message": "Stock alerts checked successfully",
            "new_alerts_count": len(new_alerts),
            "new_alerts": new_alerts
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking stock alerts: {str(e)}"
        )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Acknowledge a stock alert - Admin+ only
    """
    from app.services.stock_alert_service import StockAlertService
    
    alert_service = StockAlertService(db)
    
    try:
        alert = alert_service.acknowledge_alert(alert_id, current_user.id)
        return {"message": "Alert acknowledged", "alert": alert}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error acknowledging alert: {str(e)}"
        )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Resolve a stock alert - Admin+ only
    """
    from app.services.stock_alert_service import StockAlertService
    
    alert_service = StockAlertService(db)
    
    try:
        alert = alert_service.resolve_alert(alert_id)
        return {"message": "Alert resolved", "alert": alert}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolving alert: {str(e)}"
        )


@router.get("/alerts/history")
async def get_alert_history(
    product_id: Optional[UUID] = Query(None, description="Filter by product"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get alert history - Admin+ only
    """
    from app.services.stock_alert_service import StockAlertService
    
    alert_service = StockAlertService(db)
    
    try:
        alerts = alert_service.get_alert_history(
            product_id=product_id,
            days=days,
            skip=skip,
            limit=limit
        )
        
        return {
            "alerts": alerts,
            "total": len(alerts),
            "period_days": days,
            "page": skip // limit + 1,
            "page_size": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert history: {str(e)}"
        )


# Stock Analytics Endpoints
@router.get("/analytics/overview")
async def get_stock_analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get comprehensive stock analytics overview - Manager+ only
    """
    from app.services.stock_analytics_service import StockAnalyticsService
    
    analytics_service = StockAnalyticsService(db)
    
    try:
        overview = analytics_service.get_stock_overview()
        value_by_category = analytics_service.get_stock_value_by_category()
        
        return {
            "overview": overview,
            "value_by_category": value_by_category
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stock analytics: {str(e)}"
        )


@router.get("/analytics/trends")
async def get_stock_movement_trends(
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get stock movement trends - Manager+ only
    """
    from app.services.stock_analytics_service import StockAnalyticsService
    
    analytics_service = StockAnalyticsService(db)
    
    try:
        trends = analytics_service.get_stock_movements_trend(days=days)
        return trends
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stock trends: {str(e)}"
        )


@router.get("/analytics/turnover")
async def get_stock_turnover(
    days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get stock turnover analysis - Manager+ only
    """
    from app.services.stock_analytics_service import StockAnalyticsService
    
    analytics_service = StockAnalyticsService(db)
    
    try:
        turnover_data = analytics_service.get_stock_turnover_analysis(days=days)
        fast_moving = analytics_service.get_fast_moving_products(limit=10, days=days)
        slow_moving = analytics_service.get_slow_moving_products(limit=10, days=days)
        
        return {
            "turnover_data": turnover_data[:limit],
            "fast_moving_products": fast_moving,
            "slow_moving_products": slow_moving,
            "analysis_period_days": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving turnover analysis: {str(e)}"
        )


@router.get("/analytics/aging")
async def get_stock_aging(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get stock aging report - Manager+ only
    """
    from app.services.stock_analytics_service import StockAnalyticsService
    
    analytics_service = StockAnalyticsService(db)
    
    try:
        aging_data = analytics_service.get_stock_aging_report()
        return {
            "aging_data": aging_data[:limit],
            "total_products": len(aging_data)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving aging report: {str(e)}"
        )


@router.get("/analytics/forecast/{product_id}")
async def get_stock_forecast(
    product_id: UUID,
    days_ahead: int = Query(30, ge=1, le=90, description="Days to forecast ahead"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get stock forecast for a specific product - Manager+ only
    """
    from app.services.stock_analytics_service import StockAnalyticsService
    
    analytics_service = StockAnalyticsService(db)
    
    try:
        forecast = analytics_service.get_stock_forecast(product_id, days_ahead=days_ahead)
        return forecast
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating forecast: {str(e)}"
        )
