from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1 import deps
from app.services.delivery_service import DeliveryService
from app.schemas.delivery import DeliveryNoteCreate, DeliveryNoteResponse, DeliveryStatus

router = APIRouter()

@router.post("/", response_model=DeliveryNoteResponse)
def create_delivery_note(
    delivery_in: DeliveryNoteCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    """
    Create a new delivery note for an order.
    """
    service = DeliveryService(db)
    try:
        # Convert items schema to dict for service
        items_dict = [{"product_id": item.product_id, "quantity": item.quantity} for item in delivery_in.items]
        
        return service.create_delivery_note(
            order_id=delivery_in.order_id,
            items=items_dict,
            user_id=current_user.id,
            notes=delivery_in.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{delivery_id}", response_model=DeliveryNoteResponse)
def get_delivery_note(
    delivery_id: UUID,
    db: Session = Depends(deps.get_db)
):
    service = DeliveryService(db)
    note = service.get(delivery_id)
    if not note:
        raise HTTPException(status_code=404, detail="Delivery note not found")
    return note

@router.post("/{delivery_id}/ship", response_model=DeliveryNoteResponse)
def mark_as_shipped(
    delivery_id: UUID,
    carrier_name: str = None,
    tracking_reference: str = None,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    service = DeliveryService(db)
    try:
        return service.mark_as_shipped(delivery_id, carrier=carrier_name, tracking=tracking_reference)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{delivery_id}/deliver", response_model=DeliveryNoteResponse)
def mark_as_delivered(
    delivery_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user)
):
    service = DeliveryService(db)
    try:
        return service.mark_as_delivered(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/order/{order_id}", response_model=List[DeliveryNoteResponse])
def get_order_deliveries(
    order_id: UUID,
    db: Session = Depends(deps.get_db)
):
    service = DeliveryService(db)
    # Simple query not in service yet, doing here for speed
    # Ideally should be in service
    from app.models.delivery import DeliveryNote
    return db.query(DeliveryNote).filter(DeliveryNote.order_id == order_id).all()
