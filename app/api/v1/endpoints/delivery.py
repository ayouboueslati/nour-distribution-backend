from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.v1 import deps
from app.services.delivery_service import DeliveryService
from app.schemas.delivery import DeliveryNoteCreate, DeliveryNoteResponse, DeliveryStatus
from app.models.delivery import DeliveryNote, DeliveryStatus as DeliveryStatusModel

router = APIRouter()


@router.get("/", response_model=List[DeliveryNoteResponse])
def list_delivery_notes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, SHIPPED, DELIVERED, RETURNED"),
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """
    List all delivery notes with optional status filter.
    Returns a plain list; the frontend handles both array and {deliveries:[]} shapes.
    """
    query = db.query(DeliveryNote).options(
        joinedload(DeliveryNote.client),
        joinedload(DeliveryNote.items),
    )

    if status and status.upper() != "ALL":
        try:
            status_enum = DeliveryStatusModel(status.lower())
            query = query.filter(DeliveryNote.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    notes = query.order_by(DeliveryNote.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for note in notes:
        # Populate client_name from the eagerly-loaded relationship
        client_name: Optional[str] = None
        if note.client:
            if hasattr(note.client, "company_name") and note.client.company_name:
                client_name = note.client.company_name
            else:
                parts = [
                    getattr(note.client, "first_name", "") or "",
                    getattr(note.client, "last_name", "") or "",
                ]
                client_name = " ".join(p for p in parts if p).strip() or None

        note_dict = {
            "id": note.id,
            "delivery_number": note.delivery_number,
            "status": note.status,
            "order_id": note.order_id,
            "client_id": note.client_id,
            "client_name": client_name,
            "notes": note.notes,
            "tracking_reference": note.tracking_reference,
            "carrier_name": note.carrier_name,
            "shipped_at": note.shipped_at,
            "delivered_at": note.delivered_at,
            "created_at": note.created_at,
            "items": note.items,
        }
        results.append(DeliveryNoteResponse.model_validate(note_dict))

    return results


@router.post("/", response_model=DeliveryNoteResponse)
def create_delivery_note(
    delivery_in: DeliveryNoteCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_active_user),
):
    """
    Create a new delivery note for an order.
    """
    service = DeliveryService(db)
    try:
        items_dict = [{"product_id": item.product_id, "quantity": item.quantity} for item in delivery_in.items]
        return service.create_delivery_note(
            order_id=delivery_in.order_id,
            items=items_dict,
            user_id=current_user.id,
            notes=delivery_in.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/order/{order_id}", response_model=List[DeliveryNoteResponse])
def get_order_deliveries(
    order_id: UUID,
    db: Session = Depends(deps.get_db),
):
    """
    Get all delivery notes for a specific order.
    """
    return (
        db.query(DeliveryNote)
        .options(joinedload(DeliveryNote.items))
        .filter(DeliveryNote.order_id == order_id)
        .all()
    )


@router.get("/{delivery_id}", response_model=DeliveryNoteResponse)
def get_delivery_note(
    delivery_id: UUID,
    db: Session = Depends(deps.get_db),
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
    current_user=Depends(deps.get_current_active_user),
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
    current_user=Depends(deps.get_current_active_user),
):
    service = DeliveryService(db)
    try:
        return service.mark_as_delivered(delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
