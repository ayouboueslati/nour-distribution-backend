# app/api/v1/endpoints/carts.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.schemas.cart import (
    CartItemCreate, CartItemUpdate, CartItemResponse,
    CartResponse, CartSummary
)
from app.services.cart_service import CartService

router = APIRouter()

@router.get("/my-cart", response_model=CartResponse)
async def get_my_cart(
    client_id: UUID,  # In real app, this would come from authenticated client
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's cart with all items
    """
    cart_service = CartService(db)
    
    try:
        cart = cart_service.get_cart_with_details(client_id)
        
        if not cart:
            # Create empty cart if doesn't exist
            cart = cart_service.get_or_create_cart(client_id)
        
        # Add product details to response
        response_data = {
            "id": cart.id,
            "client_id": cart.client_id,
            "is_active": cart.is_active,
            "created_at": cart.created_at,
            "updated_at": cart.updated_at,
            "items": [],
            "total_items": len(cart.items) if cart.items else 0
        }
        
        if cart.items:
            for item in cart.items:
                item_dict = {
                    "id": item.id,
                    "cart_id": item.cart_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "reserved_at": item.reserved_at,
                    "reservation_expires_at": item.reservation_expires_at,
                    "created_at": item.created_at,
                    "product": {
                        "id": item.product.id,
                        "name": item.product.name,
                        "sku": item.product.sku,
                        "available_quantity": item.product.available_quantity,
                        "main_image": item.product.main_image
                    } if item.product else None
                }
                response_data["items"].append(item_dict)
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving cart: {str(e)}"
        )

@router.post("/items", response_model=CartItemResponse)
async def add_item_to_cart(
    client_id: UUID,
    item_data: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add item to cart - checks stock availability
    """
    cart_service = CartService(db)
    
    try:
        cart_item = cart_service.add_item_to_cart(client_id, item_data)
        return cart_item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding item to cart: {str(e)}"
        )

@router.put("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    client_id: UUID,
    item_id: UUID,
    update_data: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update cart item quantity - checks stock availability
    """
    cart_service = CartService(db)
    
    try:
        cart_item = cart_service.update_cart_item(client_id, item_id, update_data)
        return cart_item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating cart item: {str(e)}"
        )

@router.delete("/items/{item_id}")
async def remove_cart_item(
    client_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove item from cart
    """
    cart_service = CartService(db)
    
    success = cart_service.remove_cart_item(client_id, item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    return {"message": "Item removed from cart successfully"}

@router.delete("/clear")
async def clear_cart(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all items from cart
    """
    cart_service = CartService(db)
    
    cart_service.clear_cart(client_id)
    return {"message": "Cart cleared successfully"}

@router.get("/summary", response_model=CartSummary)
async def get_cart_summary(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cart summary with stock validation
    """
    cart_service = CartService(db)
    
    try:
        cart = cart_service.get_cart_with_details(client_id)
        
        if not cart or not cart.items:
            return {
                "total_items": 0,
                "total_quantity": 0,
                "has_out_of_stock": False,
                "out_of_stock_items": []
            }
        
        total_quantity = sum(item.quantity for item in cart.items)
        out_of_stock_items = []
        
        for item in cart.items:
            if item.quantity > item.product.available_quantity:
                out_of_stock_items.append({
                    "product_id": str(item.product_id),
                    "product_name": item.product.name,
                    "requested_quantity": item.quantity,
                    "available_quantity": item.product.available_quantity
                })
        
        return {
            "total_items": len(cart.items),
            "total_quantity": total_quantity,
            "has_out_of_stock": len(out_of_stock_items) > 0,
            "out_of_stock_items": out_of_stock_items
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cart summary: {str(e)}"
        )