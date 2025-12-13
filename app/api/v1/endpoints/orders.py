from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.models.order import OrderStatus
from app.schemas.order import (
    OrderCreate, OrderFromCart, OrderUpdate, OrderPricing,
    OrderResponse, OrderListResponse, OrderHistoryResponse,
    OrderItemsUpdateRequest, OrderAcceptRequest, OrderRejectRequest,
    OrderItemUpdate, OrderItemSingleUpdate, OrderItemCreate
)
from app.services.order_service import OrderService

router = APIRouter()

@router.post("/from-cart", response_model=OrderResponse)
async def create_order_from_cart(
    order_data: OrderFromCart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create order from cart - Client submits cart
    Stock is reserved for 30 days
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.create_order_from_cart(
            order_data.cart_id,
            order_data,
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating order: {str(e)}"
        )

@router.post("/", response_model=OrderResponse)
async def create_order_direct(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create order directly without cart - Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.create_order_direct(order_data, user_id=current_user.id)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating order: {str(e)}"
        )

@router.get("/", response_model=OrderListResponse)
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    order_status: Optional[str] = Query(None, description="Filter by status", alias="status"),
    client_id: Optional[UUID] = Query(None, description="Filter by client"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all orders with filtering - Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        if order_status:
            try:
                status_enum = OrderStatus(order_status)
                orders = order_service.get_orders_by_status(status_enum, skip, limit)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {order_status}"
                )
        elif client_id:
            orders = order_service.get_client_orders(client_id, skip, limit)
        else:
            orders = order_service.get_all(skip, limit)
        
        total = order_service.get_total_count()
        
        return OrderListResponse(
            orders=orders,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving orders: {str(e)}"
        )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get order details - Manager+ only
    """
    order_service = OrderService(db)
    
    order = order_service.get_order_with_details(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order

@router.put("/{order_id}/pricing", response_model=OrderResponse)
async def update_order_pricing(
    order_id: UUID,
    pricing_data: OrderPricing,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Admin sets pricing for order (traiter) - Manager+ only
    Changes status from EN_ATTENTE to EN_TRAITEMENT
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.update_order_pricing(
            order_id,
            pricing_data,
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating order pricing: {str(e)}"
        )

@router.post("/{order_id}/confirm", response_model=OrderResponse)
async def confirm_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Admin confirms order - Manager+ only
    Changes status from EN_TRAITEMENT to CONFIRME
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.confirm_order(order_id, user_id=current_user.id)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error confirming order: {str(e)}"
        )

@router.put("/{order_id}/items", response_model=OrderResponse)
async def update_order_items(
    order_id: UUID,
    items_request: OrderItemsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update order items - add, remove, or modify products
    Only allowed for PENDING or PROCESSING orders - Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        # Convert Pydantic models to dicts
        items_data = [item.model_dump() for item in items_request.items]
        order = order_service.update_order_items(order_id, items_data, user_id=current_user.id)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating order items: {str(e)}"
        )

@router.put("/{order_id}/items/{item_id}", response_model=OrderResponse)
async def update_order_item(
    order_id: UUID,
    item_id: UUID,
    item_data: OrderItemSingleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update single order item - Manager+ only
    Only allowed for PENDING or PROCESSING orders
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.update_order_item(
            order_id, 
            item_id, 
            item_data, 
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating order item: {str(e)}"
        )

@router.post("/{order_id}/items", response_model=OrderResponse)
async def add_order_item(
    order_id: UUID,
    item_data: OrderItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Add item to order - Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.add_order_item(
            order_id, 
            item_data, 
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding order item: {str(e)}"
        )

@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
async def remove_order_item(
    order_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Remove item from order - Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.remove_order_item(
            order_id, 
            item_id, 
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing order item: {str(e)}"
        )

@router.post("/{order_id}/accept", response_model=OrderResponse)
async def accept_order(
    order_id: UUID,
    accept_request: OrderAcceptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Accept order - change status from PENDING to PROCESSING
    Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.accept_order(
            order_id,
            notes=accept_request.notes,
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accepting order: {str(e)}"
        )

@router.post("/{order_id}/reject", response_model=OrderResponse)
async def reject_order(
    order_id: UUID,
    reject_request: OrderRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Reject/Cancel order - change status to CANCELLED and release stock
    Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.reject_order(
            order_id,
            reason=reject_request.reason,
            notes=reject_request.notes,
            user_id=current_user.id
        )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting order: {str(e)}"
        )

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    reason: str = Query(..., description="Reason for cancellation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Cancel order and release reserved stock - Manager+ only
    """
    order_service = OrderService(db)
    
    try:
        order = order_service.cancel_order(order_id, reason, user_id=current_user.id)
        return {
            "message": "Order cancelled successfully",
            "order_number": order.order_number
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling order: {str(e)}"
        )

@router.get("/{order_id}/history", response_model=List[OrderHistoryResponse])
async def get_order_history(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get order change history - Manager+ only
    """
    order_service = OrderService(db)
    
    order = order_service.get_order_with_details(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order.history

@router.get("/status/en-attente")
async def get_pending_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get orders waiting for admin action - Manager+ only
    """
    order_service = OrderService(db)
    
    orders = order_service.get_orders_by_status(OrderStatus.PENDING, skip, limit)
    
    return {
        "orders": orders,
        "total": len(orders),
        "status": "en_attente"
    }

@router.post("/maintenance/check-expired-reservations")
async def check_expired_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manually trigger check for expired order reservations - Manager+ only
    (This should normally run as a background task)
    """
    order_service = OrderService(db)
    
    try:
        released_orders = order_service.check_expired_reservations()
        return {
            "message": f"Checked and released {len(released_orders)} expired orders",
            "released_order_ids": [str(order_id) for order_id in released_orders]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking expired reservations: {str(e)}"
        )
