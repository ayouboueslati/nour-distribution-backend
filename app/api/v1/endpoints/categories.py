from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryResponse, 
    CategoryListResponse, CategoryNestedResponse
)
from app.services.category_service import CategoryService

router = APIRouter()

@router.get("/", response_model=CategoryListResponse)
async def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = Query(False, description="Include inactive categories"),
    db: Session = Depends(get_db)
):
    """
    Get all categories with pagination
    """
    category_service = CategoryService(db)
    
    try:
        if include_inactive:
            categories = category_service.get_all(skip=skip, limit=limit)
        else:
            categories = category_service.get_active_categories()
            # Apply pagination manually for filtered results
            categories = categories[skip:skip + limit]
        
        total = category_service.get_total_count()
        
        return CategoryListResponse(
            categories=categories,
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving categories: {str(e)}"
        )

@router.get("/tree", response_model=List[CategoryResponse])
async def get_category_tree(
    db: Session = Depends(get_db)
):
    """
    Get category hierarchy tree
    """
    category_service = CategoryService(db)
    
    try:
        category_tree = category_service.get_category_tree()
        return category_tree
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving category tree: {str(e)}"
        )

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get category by ID
    """
    category_service = CategoryService(db)
    
    category = category_service.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category

@router.get("/{category_id}/subcategories", response_model=List[CategoryResponse])
async def get_subcategories(
    category_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get subcategories of a parent category
    """
    category_service = CategoryService(db)
    
    try:
        subcategories = category_service.get_subcategories(category_id)
        return subcategories
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving subcategories: {str(e)}"
        )

@router.post("/", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create new category - Manager+ only
    """
    category_service = CategoryService(db)
    
    try:
        category = category_service.create_category(category_data)
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating category: {str(e)}"
        )

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update category - Manager+ only
    """
    category_service = CategoryService(db)
    
    try:
        category = category_service.update_category(category_id, category_data)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating category: {str(e)}"
        )

@router.delete("/{category_id}")
async def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Delete category - Manager+ only
    """
    category_service = CategoryService(db)
    
    # Check if category has products
    category = category_service.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    if category.products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with associated products"
        )
    
    success = category_service.delete(category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return {"message": "Category deleted successfully"}

@router.get("/analytics/with-product-count")
async def get_categories_with_product_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get categories with product counts - Manager+ only
    """
    category_service = CategoryService(db)
    
    try:
        categories_with_counts = category_service.get_categories_with_product_count()
        return {"categories": categories_with_counts}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving category analytics: {str(e)}"
        )

@router.get("/featured/list")
async def get_featured_categories(
    db: Session = Depends(get_db)
):
    """
    Get featured categories for homepage
    """
    category_service = CategoryService(db)
    
    try:
        featured_categories = category_service.get_featured_categories()
        return {
            "featured_categories": featured_categories,
            "total": len(featured_categories)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving featured categories: {str(e)}"
        )