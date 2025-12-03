from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.schemas.inventory import InventoryMovementCreate, InventoryMovementResponse
from app.services.inventory_service import InventoryService
from app.services.product_service import ProductService

router = APIRouter()

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