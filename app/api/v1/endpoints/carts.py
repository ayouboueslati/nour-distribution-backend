from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import json

from app.core.database import get_db
from app.schemas.cart import (
    CartItemCreate, CartItemUpdate, CartItemResponse,
    CartResponse, CartSummary
)
from app.services.cart_service import CartService

router = APIRouter()


@router.get("/guest/{guest_session_id}")
async def get_guest_cart(
    guest_session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get guest cart with all items
    Guest Session ID is created by frontend and stored in localStorage
    """
    cart_service = CartService(db)
    
    try:
        cart = cart_service.get_cart_with_details(guest_session_id)
        
        if not cart:
            # Create empty cart if doesn't exist
            cart = cart_service.get_or_create_cart(guest_session_id)
        
        # Add product details to response
        response_data = {
            "id": str(cart.id),
            "guest_session_id": str(cart.guest_session_id),
            "is_active": cart.is_active,
            "created_at": cart.created_at.isoformat(),
            "updated_at": cart.updated_at.isoformat(),
            "items": [],
            "total_items": len(cart.items) if cart.items else 0
        }
        
        if cart.items:
            for item in cart.items:
                item_dict = {
                    "id": str(item.id),
                    "cart_id": str(item.cart_id),
                    "product_id": str(item.product_id),
                    "quantity": item.quantity,
                    "reserved_at": item.reserved_at.isoformat() if item.reserved_at else None,
                    "reservation_expires_at": item.reservation_expires_at.isoformat() if item.reservation_expires_at else None,
                    "created_at": item.created_at.isoformat(),
                    "product": {
                        "id": str(item.product.id),
                        "name": item.product.name,
                        "sku": item.product.sku,
                        "available_quantity": item.product.available_quantity,
                        "main_image": item.product.main_image,
                        "is_active": item.product.is_active
                    } if item.product else None
                }
                response_data["items"].append(item_dict)
        
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving cart: {str(e)}"
        )


# app/api/v1/endpoints/carts.py - Update all endpoints
@router.post("/guest/{guest_session_id}/items")
async def add_item_to_guest_cart(
    guest_session_id: str,  # Changed from UUID to string for flexibility
    item_data: CartItemCreate,
    db: Session = Depends(get_db)
):
    """
    Add item to guest cart - checks stock availability
    """
    cart_service = CartService(db)
    
    print(f"DEBUG: Adding item to guest cart - guest_session_id: {guest_session_id}")
    
    try:
        cart_item = cart_service.add_item_to_cart(guest_session_id, item_data)
        
        return {
            "success": True,
            "message": "Article ajouté au panier",
            "item": {
                "id": str(cart_item.id),
                "product_id": str(cart_item.product_id),
                "quantity": cart_item.quantity,
                "product_name": cart_item.product.name if cart_item.product else None
            }
        }
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

@router.put("/guest/{guest_session_id}/items/{item_id}")
async def update_guest_cart_item(
    guest_session_id: str,
    item_id: UUID,
    update_data: CartItemUpdate,
    db: Session = Depends(get_db)
):
    """
    Update cart item quantity - checks stock availability
    """
    cart_service = CartService(db)
    
    try:
        cart_item = cart_service.update_cart_item(guest_session_id, item_id, update_data)
        
        return {
            "success": True,
            "message": "Quantité mise à jour",
            "item": {
                "id": str(cart_item.id),
                "product_id": str(cart_item.product_id),
                "quantity": cart_item.quantity,
                "product_name": cart_item.product.name if cart_item.product else None
            }
        }
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


@router.delete("/guest/{guest_session_id}/items/{item_id}")
async def remove_guest_cart_item(
    guest_session_id: str,
    item_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Remove item from guest cart
    """
    cart_service = CartService(db)
    
    success = cart_service.remove_cart_item(guest_session_id, item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article introuvable dans le panier"
        )
    
    return {
        "success": True,
        "message": "Article retiré du panier"
    }


@router.delete("/guest/{guest_session_id}/clear")
async def clear_guest_cart(
    guest_session_id: str,
    db: Session = Depends(get_db)
):
    """
    Clear all items from guest cart
    """
    cart_service = CartService(db)
    
    cart_service.clear_cart(guest_session_id)
    return {
        "success": True,
        "message": "Panier vidé"
    }


@router.get("/guest/{guest_session_id}/summary")
async def get_guest_cart_summary(
    guest_session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get cart summary with stock validation for guests
    """
    cart_service = CartService(db)
    
    try:
        cart = cart_service.get_cart_with_details(guest_session_id)
        
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


from app.schemas.client import GuestCheckoutRequest

@router.post("/guest/{guest_session_id}/checkout")
async def guest_checkout(
    guest_session_id: str,
    checkout_request: GuestCheckoutRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Convert guest cart to order - creates client record ONLY at checkout
    """
    from app.models.client import Client, ClientType
    from app.services.order_service import OrderService
    from app.schemas.order import OrderFromCart
    from app.models.cart import Cart
    
    # Debug logging - detailed
    print("=" * 80)
    print("DEBUG CHECKOUT REQUEST")
    print("=" * 80)
    print(f"Guest Session ID: {guest_session_id}")
    print(f"Request Type: {type(checkout_request)}")
    print(f"Is Company: {checkout_request.is_company}")
    print(f"B2C Data: {checkout_request.b2c_data}")
    print(f"B2B Data: {checkout_request.b2b_data}")
    if checkout_request.b2c_data:
        print(f"  B2C - First Name: {checkout_request.b2c_data.first_name}")
        print(f"  B2C - Phone: {checkout_request.b2c_data.phone}")
    if checkout_request.b2b_data:
        print(f"  B2B - Company: {checkout_request.b2b_data.company_name}")
        print(f"  B2B - Phone: {checkout_request.b2b_data.phone}")
    print("=" * 80)
    
    cart_service = CartService(db)
    order_service = OrderService(db)
    
    # Get cart by guest_session_id
    cart = db.query(Cart).filter(
        Cart.guest_session_id == guest_session_id,
        Cart.is_active == True
    ).first()
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Panier introuvable"
        )
    
    # Validate cart has items
    if not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Panier vide"
        )
    
    try:
        # CREATE CLIENT RECORD (only at checkout!)
        from uuid import uuid4
        
        # Determine client type and extract data
        if checkout_request.is_company:
            client_type = ClientType.B2B
            data = checkout_request.b2b_data
            if not data:
                raise ValueError("B2B data is required for company orders")
            
            # Create B2B client
            client = Client(
                id=uuid4(),
                type=client_type,
                company_name=data.company_name,
                fiscal_id=data.fiscal_id,
                contact_name=data.contact_name,
                phone=data.phone,
                email=data.email,
                address=data.address,
                payment_method=data.payment_method,
                notes=data.notes,
                is_active=True
            )
            delivery_notes = data.notes or ''
        else:
            client_type = ClientType.B2C
            data = checkout_request.b2c_data
            if not data:
                raise ValueError("B2C data is required for individual orders")
            
            # Create B2C client
            client = Client(
                id=uuid4(),
                type=client_type,
                first_name=data.first_name,
                last_name=data.last_name,
                phone=data.phone,
                email=data.email,
                address=data.address,
                preferred_contact_method=data.preferred_contact,
                is_active=True
            )
            delivery_notes = data.delivery_notes or ''
        
        db.add(client)
        db.flush()  # Get the client ID
        
        # Create order from cart
        order_data = OrderFromCart(
            cart_id=cart.id,
            shipping_address=data.address,
            delivery_notes=delivery_notes
        )
        
        order = order_service.create_order_from_cart(
            cart.id,
            client.id,  # Pass the newly created client ID
            order_data,
            user_id=None  # No user for guest checkout
        )
        
        # Mark cart as inactive (converted to order)
        cart.is_active = False
        
        db.commit()
        
        return {
            "success": True,
            "message": "Commande créée avec succès",
            "order": {
                "id": str(order.id),
                "order_number": order.order_number,
                "status": order.status.value,
                "total_items": len(order.items),
                "client_id": str(client.id),
                "tracking_info": {
                    "order_number": order.order_number,
                    "verification_code": client.phone or client.email,
                    "message": "Conservez ces informations pour suivre votre commande"
                }
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating order: {str(e)}"
        )