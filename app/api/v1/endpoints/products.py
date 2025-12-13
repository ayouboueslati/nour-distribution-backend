from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import json

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_admin, require_manager
from app.models.user import User
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductPublicResponse, 
    ProductAdminResponse, ProductListResponse, ProductAdminListResponse,
    StockUpdate
)
from app.schemas.product_image import ProductImageCreate, ProductImageResponse
from app.services.product_service import ProductService
from app.services.category_service import CategoryService
from app.services.supplier_service import SupplierService

router = APIRouter()

@router.get("/", response_model=ProductListResponse)
async def get_products(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    supplier_id: Optional[UUID] = Query(None, description="Filter by supplier"),
    hair_type: Optional[str] = Query(None, description="Filter by hair type"),
    hair_length: Optional[str] = Query(None, description="Filter by hair length"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, SKU, description"),
    db: Session = Depends(get_db)
):
    """
    Get products with advanced filtering and search
    """
    product_service = ProductService(db)
    
    try:
        products = product_service.get_products_with_filters(
            skip=skip,
            limit=limit,
            category_id=category_id,
            supplier_id=supplier_id,
            hair_type=hair_type,
            hair_length=hair_length,
            is_active=is_active,
            search_term=search
        )
        
        total = product_service.get_total_count()
        
        return ProductListResponse(
            products=products,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products: {str(e)}"
        )

@router.get("/admin", response_model=ProductAdminListResponse)
async def get_products_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get products with admin details (pricing, full inventory) - Manager+ only
    """
    product_service = ProductService(db)
    
    try:
        products = product_service.get_products_with_filters(
            skip=skip,
            limit=limit,
            category_id=category_id,
            supplier_id=supplier_id,
            is_active=is_active,
            search_term=search
        )
        
        total = product_service.get_total_count()
        
        return ProductAdminListResponse(
            products=products,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products: {str(e)}"
        )

@router.get("/{product_id}", response_model=ProductPublicResponse)
async def get_product(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get product by ID (public details)
    """
    product_service = ProductService(db)
    
    product = product_service.get_product_with_details(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product

@router.get("/admin/{product_id}", response_model=ProductAdminResponse)
async def get_product_admin(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get product by ID with admin details (pricing, inventory) - Manager+ only
    """
    product_service = ProductService(db)
    
    product = product_service.get_product_with_details(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product

@router.post("/", response_model=ProductAdminResponse)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create new product - Manager+ only
    """
    product_service = ProductService(db)
    
    try:
        product = product_service.create_product(product_data)
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {str(e)}"
        )

@router.put("/{product_id}", response_model=ProductAdminResponse)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update product - Manager+ only
    """
    product_service = ProductService(db)
    
    try:
        product = product_service.update_product(product_id, product_data)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating product: {str(e)}"
        )

@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete product - Admin+ only
    """
    product_service = ProductService(db)
    
    success = product_service.delete_product(product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return {"message": "Product deleted successfully"}

@router.patch("/{product_id}/stock", response_model=ProductAdminResponse)
async def update_product_stock(
    product_id: UUID,
    stock_data: StockUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update product stock with reason - Manager+ only
    """
    product_service = ProductService(db)
    
    try:
        product = product_service.update_stock(
            product_id, 
            stock_data, 
            user_id=current_user.id
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        return product
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating stock: {str(e)}"
        )

@router.get("/{product_id}/low-stock")
async def check_low_stock(
    product_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if product needs restocking
    """
    product_service = ProductService(db)
    
    product = product_service.get_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "current_stock": product.stock_quantity,
        "min_stock_level": product.min_stock_level,
        "needs_restock": product.needs_restock,
        "available_quantity": product.available_quantity
    }

@router.get("/analytics/low-stock")
async def get_low_stock_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all products that need restocking - Manager+ only
    """
    product_service = ProductService(db)
    
    try:
        low_stock_products = product_service.get_low_stock_products()
        return {
            "low_stock_products": low_stock_products,
            "total": len(low_stock_products)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving low stock alerts: {str(e)}"
        )

@router.get("/analytics/featured")
async def get_featured_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get featured products for homepage
    """
    product_service = ProductService(db)
    
    try:
        featured_products = product_service.get_featured_products()
        return {
            "featured_products": featured_products,
            "total": len(featured_products)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving featured products: {str(e)}"
        )

@router.get("/analytics/best-sellers")
async def get_best_sellers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get best-selling products
    """
    product_service = ProductService(db)
    
    try:
        best_sellers = product_service.get_best_sellers()
        return {
            "best_sellers": best_sellers,
            "total": len(best_sellers)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving best sellers: {str(e)}"
        )

@router.get("/supplier/{supplier_id}")
async def get_products_by_supplier(
    supplier_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all products from a specific supplier - Manager+ only
    """
    product_service = ProductService(db)
    
    try:
        products = product_service.get_products_by_supplier(supplier_id)
        
        # Apply pagination
        paginated_products = products[skip:skip + limit]
        
        return {
            "products": paginated_products,
            "total": len(products),
            "page": skip // limit + 1,
            "page_size": limit
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving supplier products: {str(e)}"
        )