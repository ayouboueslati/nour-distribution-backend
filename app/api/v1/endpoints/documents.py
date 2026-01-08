# app/api/v1/endpoints/documents.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional
from uuid import UUID
import io

from app.core.database import get_db
from app.api.v1.deps import get_current_user, require_manager
from app.models.user import User
from app.models.document import DocumentType, DocumentStatus, Document
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DevisFromOrder,
    DocumentResponse, DocumentListResponse,
    DocumentHistoryResponse, PaymentCreate, PaymentResponse,
    AvoirFromFacture, PaginatedDevisResponse
)
from app.services.document_service import DocumentService
from app.services.pdf_service import PDFService
from fastapi.responses import StreamingResponse

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
    
    # Compare values instead of Enum objects since schemas/models define Enums differently
    if facture_data.type.value != DocumentType.FACTURE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document type must be FACTURE (got {facture_data.type})"
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

# ==================== DEVIS TRACKING ENDPOINTS ====================

# Alternative endpoint path for frontend compatibility
@router.get("/devis/by-order/{order_id}", response_model=PaginatedDevisResponse)
async def get_devis_by_order(
    order_id: UUID,
    include_versions: bool = Query(False, description="Include all versions, not just latest"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all devis for a specific order (alternative path for frontend)
    """
    document_service = DocumentService(db)
    
    try:
        devis_list, total = document_service.get_devis_by_order(
            order_id=order_id,
            include_versions=include_versions,
            skip=skip,
            limit=limit
        )
        
        page = skip // limit + 1
        has_next = (skip + limit) < total
        has_previous = skip > 0
        
        return PaginatedDevisResponse(
            devis_list=devis_list,
            total=total,
            page=page,
            page_size=limit,
            has_next=has_next,
            has_previous=has_previous
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving order devis: {str(e)}"
        )

# Alternative endpoint for factures by order
@router.get("/factures/by-order/{order_id}", response_model=List[DocumentResponse])
async def get_factures_by_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all factures for a specific order
    """
    from app.models.document import DocumentType
    
    document_service = DocumentService(db)
    
    try:
        # Query factures by order_id
        factures = db.query(Document).filter(
            and_(
                Document.order_id == order_id,
                Document.type == DocumentType.FACTURE,
                Document.is_latest_version == True
            )
        ).options(
            joinedload(Document.items),
            joinedload(Document.client)
        ).all()
        
        return factures
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving factures: {str(e)}"
        )

@router.get("/orders/{order_id}/devis", response_model=PaginatedDevisResponse)
async def get_order_devis(
    order_id: UUID,
    include_versions: bool = Query(False, description="Include all versions, not just latest"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get all devis for a specific order with pagination - Manager+ only
    Shows all devis created for this order, optionally including all versions.
    Includes canceled devis as well.
    """
    document_service = DocumentService(db)
    
    try:
        devis_list, total = document_service.get_devis_by_order(
            order_id=order_id,
            include_versions=include_versions,
            skip=skip,
            limit=limit
        )
        
        page = skip // limit + 1
        has_next = (skip + limit) < total
        has_previous = skip > 0
        
        return PaginatedDevisResponse(
            devis_list=devis_list,
            total=total,
            page=page,
            page_size=limit,
            has_next=has_next,
            has_previous=has_previous
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving order devis: {str(e)}"
        )

@router.get("/factures/{facture_id}/source-devis", response_model=DocumentResponse)
async def get_facture_source_devis(
    facture_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get the source devis that was converted to this facture - Manager+ only
    Returns the devis that this facture was created from.
    """
    document_service = DocumentService(db)
    
    try:
        devis = document_service.get_facture_source_devis(facture_id)
        
        if not devis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source devis not found. This facture may have been created directly."
            )
        
        return devis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving source devis: {str(e)}"
        )

@router.get("/orders/{order_id}/devis/timeline")
async def get_order_devis_timeline(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Get timeline of all devis events for an order - Manager+ only
    Returns a chronological list of all devis-related events including:
    - Creation
    - Modifications (new versions)
    - Acceptance
    - Conversion to facture
    - Cancellation
    """
    document_service = DocumentService(db)
    
    try:
        timeline = document_service.get_devis_timeline(order_id)
        
        return {
            "order_id": str(order_id),
            "total_events": len(timeline),
            "events": timeline
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving devis timeline: {str(e)}"
        )

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

@router.post("/utils/check-overdue")
async def check_overdue_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Manually check for overdue invoices and mark them.
    Trigger this via cron or manually.
    """
    document_service = DocumentService(db)
    try:
        count = document_service.check_overdue_invoices()
        return {"message": "Overdue check completed", "updated_count": count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking overdue invoices: {str(e)}"
        )

@router.get("/{document_id}/pdf")
@router.get("/devis/{document_id}/pdf")
@router.get("/factures/{document_id}/pdf")
@router.get("/avoirs/{document_id}/pdf")
async def get_document_pdf(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager)
):
    """
    Generate and download PDF for a document (Devis, Facture, Avoir)
    """
    document_service = DocumentService(db)
    document = document_service.get_document_with_details(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    pdf_service = PDFService()
    try:
        pdf_bytes = pdf_service.generate_pdf(document)
        
        filename = f"{document.type.value}_{document.document_number}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF: {str(e)}"
        )