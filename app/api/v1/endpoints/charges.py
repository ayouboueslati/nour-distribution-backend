from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.api.v1.deps import require_manager
from app.schemas.charge import ChargeCreate, ChargeUpdate, ChargeResponse
from app.services.charge_service import ChargeService
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[ChargeResponse])
async def get_charges(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Get all manual charges - Manager+ only"""
    charge_service = ChargeService(db)
    return charge_service.get_charges(skip=skip, limit=limit)

@router.get("/{charge_id}", response_model=ChargeResponse)
async def get_charge(
    charge_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Get a specific charge - Manager+ only"""
    charge_service = ChargeService(db)
    charge = charge_service.get_charge(charge_id)
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    return charge

@router.post("/", response_model=ChargeResponse, status_code=status.HTTP_201_CREATED)
async def create_charge(
    charge_in: ChargeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Create a new manual charge - Manager+ only"""
    charge_service = ChargeService(db)
    return charge_service.create_charge(charge_in)

@router.put("/{charge_id}", response_model=ChargeResponse)
async def update_charge(
    charge_id: UUID,
    charge_in: ChargeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Update a specific charge - Manager+ only"""
    charge_service = ChargeService(db)
    charge = charge_service.update_charge(charge_id, charge_in)
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    return charge

@router.delete("/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_charge(
    charge_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """Delete a specific charge - Manager+ only"""
    charge_service = ChargeService(db)
    if not charge_service.delete_charge(charge_id):
        raise HTTPException(status_code=404, detail="Charge not found")
    return None
