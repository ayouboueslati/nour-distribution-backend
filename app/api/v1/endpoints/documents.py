# app/api/v1/endpoints/documents.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.models.document import DocumentType, DocumentStatus
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DevisFromOrder,
    DocumentResponse, DocumentListResponse,
    DocumentHistoryResponse, PaymentCreate, PaymentResponse,
    AvoirFromFacture
)
from app.services.document_service import DocumentService

router = APIRouter()

# ==================== DEVIS ENDPOINTS ====================

@router.post("/devis/from-order", response_model=DocumentResponse)
async def create_devis_from_order(
    devis_data: DevisFromOrder,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create a devis from a confirmed order - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        devis = document_service.create_devis_from_order(
            devis_data.order_id,
            devis_data,
            user_id=current_user.id
        )
        return devis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating devis: {str(e)}"
        )

@router.get("/devis", response_model=DocumentListResponse)
async def get_all_devis(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    client_id: Optional[UUID] = Query(None, description="Filter by client"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all devis - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        if client_id:
            documents = document_service.get_client_documents(
                client_id,
                DocumentType.DEVIS,
                skip,
                limit
            )
        else:
            documents = document_service.get_documents_by_type(
                DocumentType.DEVIS,
                skip,
                limit
            )
        
        
        # Filter by status if provided
        if status_filter:
            try:
                status_enum = DocumentStatus(status_filter)
                documents = [doc for doc in documents if doc.status == status_enum]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        total = len(documents)
        
        return DocumentListResponse(
            documents=documents,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving devis: {str(e)}"
        )

@router.get("/devis/{devis_id}", response_model=DocumentResponse)
async def get_devis(
    devis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get devis details with full history - Manager+ only
    """
    document_service = DocumentService(db)
    
    devis = document_service.get_document_with_details(devis_id)
    if not devis or devis.type != DocumentType.DEVIS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Devis not found"
        )
    
    return devis

@router.put("/devis/{devis_id}", response_model=DocumentResponse)
async def update_devis(
    devis_id: UUID,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update devis (modifier) - Creates new version if significant changes - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        devis = document_service.update_document(
            devis_id,
            update_data,
            user_id=current_user.id
        )
        return devis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating devis: {str(e)}"
        )

@router.post("/devis/{devis_id}/accept", response_model=DocumentResponse)
async def accept_devis(
    devis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Accept devis (accepter) - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        devis = document_service.accept_devis(devis_id, user_id=current_user.id)
        return devis
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accepting devis: {str(e)}"
        )

@router.post("/devis/{devis_id}/convert-to-facture", response_model=DocumentResponse)
async def convert_devis_to_facture(
    devis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Convert accepted devis to facture (facturer) - Manager+ only
    This reduces actual stock and creates a facture
    """
    document_service = DocumentService(db)
    
    try:
        facture = document_service.convert_devis_to_facture(
            devis_id,
            user_id=current_user.id
        )
        return facture
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting devis to facture: {str(e)}"
        )

@router.get("/devis/{devis_id}/versions", response_model=List[DocumentResponse])
async def get_devis_versions(
    devis_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all versions of a devis - Shows history of changes - Manager+ only
    """
    document_service = DocumentService(db)
    
    devis = document_service.get_by_id(devis_id)
    if not devis or devis.type != DocumentType.DEVIS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Devis not found"
        )
    
    versions = document_service.get_document_versions(devis.document_number)
    return versions

# ==================== FACTURE ENDPOINTS ====================

@router.post("/factures", response_model=DocumentResponse)
async def create_facture(
    facture_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create a facture directly (not from devis) - Manager+ only
    """
    document_service = DocumentService(db)
    
    if facture_data.type != DocumentType.FACTURE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document type must be FACTURE"
        )
    
    try:
        facture = document_service.create_document(
            facture_data,
            user_id=current_user.id
        )
        return facture
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating facture: {str(e)}"
        )

@router.get("/factures", response_model=DocumentListResponse)
async def get_all_factures(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    payment_status: Optional[str] = Query(None, description="Filter by payment status"),
    client_id: Optional[UUID] = Query(None, description="Filter by client"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all factures - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        if client_id:
            documents = document_service.get_client_documents(
                client_id,
                DocumentType.FACTURE,
                skip,
                limit
            )
        else:
            documents = document_service.get_documents_by_type(
                DocumentType.FACTURE,
                skip,
                limit
            )
        
        total = len(documents)
        
        return DocumentListResponse(
            documents=documents,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving factures: {str(e)}"
        )

@router.get("/factures/{facture_id}", response_model=DocumentResponse)
async def get_facture(
    facture_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get facture details - Manager+ only
    """
    document_service = DocumentService(db)
    
    facture = document_service.get_document_with_details(facture_id)
    if not facture or facture.type != DocumentType.FACTURE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facture not found"
        )
    
    return facture

@router.put("/factures/{facture_id}", response_model=DocumentResponse)
async def update_facture(
    facture_id: UUID,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Update facture (modifier) - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        facture = document_service.update_document(
            facture_id,
            update_data,
            user_id=current_user.id
        )
        return facture
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating facture: {str(e)}"
        )

@router.post("/factures/{facture_id}/payments", response_model=PaymentResponse)
async def add_payment_to_facture(
    facture_id: UUID,
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Add payment to facture (paiement) - Manager+ only
    """
    document_service = DocumentService(db)
    
    # Ensure payment is for the correct facture
    if payment_data.document_id != facture_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment document_id must match facture_id"
        )
    
    try:
        payment = document_service.add_payment(
            payment_data,
            user_id=current_user.id
        )
        return payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding payment: {str(e)}"
        )

# ==================== AVOIR ENDPOINTS ====================

@router.post("/avoirs/from-facture", response_model=DocumentResponse)
async def create_avoir_from_facture(
    avoir_data: AvoirFromFacture,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Create avoir from facture - Manager+ only
    Can be for full refund or partial (some items)
    Stock is returned to inventory
    """
    document_service = DocumentService(db)
    
    try:
        avoir = document_service.create_avoir_from_facture(
            avoir_data,
            user_id=current_user.id
        )
        return avoir
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating avoir: {str(e)}"
        )

@router.get("/avoirs", response_model=DocumentListResponse)
async def get_all_avoirs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    client_id: Optional[UUID] = Query(None, description="Filter by client"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all avoirs - Manager+ only
    """
    document_service = DocumentService(db)
    
    try:
        if client_id:
            documents = document_service.get_client_documents(
                client_id,
                DocumentType.AVOIR,
                skip,
                limit
            )
        else:
            documents = document_service.get_documents_by_type(
                DocumentType.AVOIR,
                skip,
                limit
            )
        
        total = len(documents)
        
        return DocumentListResponse(
            documents=documents,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving avoirs: {str(e)}"
        )

@router.get("/avoirs/{avoir_id}", response_model=DocumentResponse)
async def get_avoir(
    avoir_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get avoir details - Manager+ only
    """
    document_service = DocumentService(db)
    
    avoir = document_service.get_document_with_details(avoir_id)
    if not avoir or avoir.type != DocumentType.AVOIR:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avoir not found"
        )
    
    return avoir

# ==================== GENERAL DOCUMENT ENDPOINTS ====================

@router.get("/{document_id}/history", response_model=List[DocumentHistoryResponse])
async def get_document_history(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get document change history - Manager+ only
    """
    document_service = DocumentService(db)
    
    document = document_service.get_document_with_details(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document.history

@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Delete document (supprimer) - Manager+ only
    Can only delete drafts or cancelled documents
    """
    document_service = DocumentService(db)
    
    document = document_service.get_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if document can be deleted
    if document.status not in [DocumentStatus.BROUILLON, DocumentStatus.ANNULE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete draft or cancelled documents"
        )
    
    success = document_service.delete(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document"
        )
    
    return {"message": f"{document.type.value.capitalize()} deleted successfully"}