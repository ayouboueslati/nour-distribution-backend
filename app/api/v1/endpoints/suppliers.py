from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.schemas.supplier import (
    SupplierCreate, SupplierUpdate, SupplierResponse, 
    SupplierListResponse, SupplierNestedResponse
)
from app.services.supplier_service import SupplierService

router = APIRouter()

@router.get("/", response_model=SupplierListResponse)
async def get_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_preferred: Optional[bool] = Query(None, description="Filter by preferred status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all suppliers - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    try:
        suppliers = supplier_service.get_all(skip=skip, limit=limit)
        
        # Apply additional filters
        if is_active is not None:
            suppliers = [s for s in suppliers if s.is_active == is_active]
        if is_preferred is not None:
            suppliers = [s for s in suppliers if s.is_preferred == is_preferred]
        
        total = supplier_service.get_total_count()
        
        return SupplierListResponse(
            suppliers=suppliers,
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving suppliers: {str(e)}"
        )

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get supplier by ID - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    supplier = supplier_service.get_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier

@router.post("/", response_model=SupplierResponse)
async def create_supplier(
    supplier_data: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create new supplier - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    try:
        supplier = supplier_service.create_supplier(supplier_data)
        return supplier
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating supplier: {str(e)}"
        )

@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    supplier_data: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update supplier - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    try:
        supplier = supplier_service.update_supplier(supplier_id, supplier_data)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found"
            )
        return supplier
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating supplier: {str(e)}"
        )

@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Delete supplier - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    # Check if supplier has products
    supplier = supplier_service.get_by_id(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    if supplier.products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete supplier with associated products"
        )
    
    success = supplier_service.delete(supplier_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return {"message": "Supplier deleted successfully"}

@router.get("/analytics/with-stats")
async def get_suppliers_with_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get suppliers with product counts and performance stats - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    try:
        suppliers_with_stats = supplier_service.get_suppliers_with_stats()
        return {"suppliers": suppliers_with_stats}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving supplier analytics: {str(e)}"
        )

@router.get("/{supplier_id}/performance")
async def get_supplier_performance(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get detailed performance metrics for a supplier - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    try:
        performance_metrics = supplier_service.get_supplier_performance_metrics(supplier_id)
        return performance_metrics
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving supplier performance: {str(e)}"
        )

@router.get("/preferred/list")
async def get_preferred_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get preferred suppliers - Manager+ only
    """
    supplier_service = SupplierService(db)
    
    try:
        preferred_suppliers = supplier_service.get_preferred_suppliers()
        return {
            "preferred_suppliers": preferred_suppliers,
            "total": len(preferred_suppliers)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving preferred suppliers: {str(e)}"
        )