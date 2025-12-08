from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.models.client import ClientType
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse
)
from app.services.client_service import ClientService

router = APIRouter()

@router.get("/", response_model=ClientListResponse)
async def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    client_type: Optional[str] = Query(None, description="Filter by type (b2b or b2c)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all clients with filtering - Manager+ only
    """
    client_service = ClientService(db)
    
    try:
        if search:
            clients = client_service.search_clients(search, skip, limit)
        elif client_type:
            try:
                type_enum = ClientType(client_type)
                clients = client_service.get_clients_by_type(type_enum, skip, limit)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid client type: {client_type}"
                )
        elif is_active is not None:
            if is_active:
                clients = client_service.get_active_clients(skip, limit)
            else:
                all_clients = client_service.get_all(skip, limit)
                clients = [c for c in all_clients if not c.is_active]
        else:
            clients = client_service.get_all(skip, limit)
        
        total = client_service.get_total_count()
        
        return ClientListResponse(
            clients=clients,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving clients: {str(e)}"
        )

@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get client by ID - Manager+ only
    """
    client_service = ClientService(db)
    
    client = client_service.get_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return client

@router.post("/", response_model=ClientResponse)
async def create_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create new client - Manager+ only
    """
    client_service = ClientService(db)
    
    try:
        client = client_service.create_client(client_data)
        return client
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating client: {str(e)}"
        )

@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update client - Manager+ only
    """
    client_service = ClientService(db)
    
    try:
        client = client_service.update_client(client_id, client_data)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        return client
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating client: {str(e)}"
        )

@router.delete("/{client_id}")
async def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Delete client - Manager+ only
    """
    client_service = ClientService(db)
    
    # Check if client has orders or documents
    client = client_service.get_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    if client.orders or client.documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete client with existing orders or documents. Deactivate instead."
        )
    
    success = client_service.delete(client_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    return {"message": "Client deleted successfully"}

@router.get("/{client_id}/stats")
async def get_client_stats(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get client statistics (orders, revenue, etc.) - Manager+ only
    """
    client_service = ClientService(db)
    
    try:
        stats = client_service.get_client_stats(client_id)
        return stats
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving client stats: {str(e)}"
        )

@router.patch("/{client_id}/deactivate")
async def deactivate_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Deactivate client (soft delete) - Manager+ only
    """
    client_service = ClientService(db)
    
    client = client_service.get_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    client.is_active = False
    client_service.db.commit()
    
    return {"message": "Client deactivated successfully"}

@router.patch("/{client_id}/activate")
async def activate_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Activate client - Manager+ only
    """
    client_service = ClientService(db)
    
    client = client_service.get_by_id(client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    client.is_active = True
    client_service.db.commit()
    
    return {"message": "Client activated successfully"}