from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import os
from app.core.database import get_db
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.models.document import Document, DocumentType, DocumentStatus
from app.services.order_service import OrderService
from app.services.document_service import DocumentService
from app.services.pdf_generator import TunisianPDFGenerator

router = APIRouter()


# ============================================================================
# PUBLIC ENDPOINTS - NO AUTHENTICATION REQUIRED
# ============================================================================

@router.post("/verify-order")
async def verify_order_access(
    order_number: str = Query(..., description="Order number (e.g., CMD-20241208-0001)"),
    verification_code: str = Query(..., description="Phone or email for verification"),
    db: Session = Depends(get_db)
):
    """
    Verify access to order using order number + phone/email
    Returns order ID if verification successful
    """
    # Find order by order number
    order = db.query(Order).filter(Order.order_number == order_number).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )
    
    # Get client
    client = order.client
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client introuvable"
        )
    
    # Verify using phone or email
    verification_code_clean = verification_code.strip().lower()
    client_phone = (client.phone or "").strip().lower()
    client_email = (client.email or "").strip().lower()
    
    if verification_code_clean not in [client_phone, client_email]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Code de vérification incorrect"
        )
    
    return {
        "success": True,
        "order_id": str(order.id),
        "order_number": order.order_number,
        "client_name": client.company_name or f"{client.first_name} {client.last_name}",
        "message": "Accès autorisé"
    }


@router.get("/orders/{order_id}")
async def get_order_details(
    order_id: UUID,
    verification: str = Query(..., description="Phone or email for verification"),
    db: Session = Depends(get_db)
):
    """
    Get order details - PUBLIC endpoint with verification
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )
    
    client = order.client
    
    # Verify access
    verification_clean = verification.strip().lower()
    if verification_clean not in [(client.phone or "").strip().lower(), (client.email or "").strip().lower()]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    # Get related documents
    documents = db.query(Document).filter(
        Document.order_id == order_id,
        Document.client_id == client.id
    ).all()
    
    return {
        "order": {
            "id": str(order.id),
            "order_number": order.order_number,
            "status": order.status.value,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "processed_at": order.processed_at.isoformat() if order.processed_at else None,
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
            "subtotal": order.subtotal,
            "shipping_fee": order.shipping_fee,
            "discount": order.discount,
            "tax_amount": order.tax_amount,
            "total_amount": order.total_amount,
            "shipping_address": order.shipping_address,
            "delivery_notes": order.delivery_notes,
            "items": [
                {
                    "product_id": str(item.product_id),
                    "product_name": item.product.name if item.product else "Unknown",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "subtotal": item.subtotal
                }
                for item in order.items
            ]
        },
        "client": {
            "name": client.company_name or f"{client.first_name} {client.last_name}",
            "type": client.type.value,
            "phone": client.phone,
            "email": client.email,
            "address": client.address
        },
        "documents": [
            {
                "id": str(doc.id),
                "type": doc.type.value,
                "document_number": doc.document_number,
                "status": doc.status.value,
                "issue_date": doc.issue_date.isoformat() if doc.issue_date else None,
                "due_date": doc.due_date.isoformat() if doc.due_date else None,
                "total_amount": doc.total_amount,
                "payment_status": doc.payment_status.value,
                "paid_amount": doc.paid_amount,
                "remaining_amount": doc.remaining_amount,
                "pdf_url": f"/api/v1/public/documents/{doc.id}/pdf"
            }
            for doc in documents
        ]
    }


@router.post("/verify-document")
async def verify_document_access(
    document_number: str = Query(..., description="Document number (e.g., DEV-20241208-0001)"),
    verification_code: str = Query(..., description="Phone or email for verification"),
    db: Session = Depends(get_db)
):
    """
    Verify access to document using document number + phone/email
    """
    # Find document by number
    document = db.query(Document).filter(Document.document_number == document_number).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document introuvable"
        )
    
    client = document.client
    
    # Verify
    verification_clean = verification_code.strip().lower()
    if verification_clean not in [(client.phone or "").strip().lower(), (client.email or "").strip().lower()]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Code de vérification incorrect"
        )
    
    return {
        "success": True,
        "document_id": str(document.id),
        "document_number": document.document_number,
        "document_type": document.type.value,
        "client_name": client.company_name or f"{client.first_name} {client.last_name}",
        "message": "Accès autorisé"
    }


@router.get("/documents/{document_id}")
async def get_document_details(
    document_id: UUID,
    verification: str = Query(..., description="Phone or email for verification"),
    db: Session = Depends(get_db)
):
    """
    Get document details - PUBLIC endpoint with verification
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document introuvable"
        )
    
    client = document.client
    
    # Verify access
    verification_clean = verification.strip().lower()
    if verification_clean not in [(client.phone or "").strip().lower(), (client.email or "").strip().lower()]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    return {
        "id": str(document.id),
        "type": document.type.value,
        "document_number": document.document_number,
        "status": document.status.value,
        "issue_date": document.issue_date.isoformat() if document.issue_date else None,
        "due_date": document.due_date.isoformat() if document.due_date else None,
        "accepted_date": document.accepted_date.isoformat() if document.accepted_date else None,
        "total_amount": document.total_amount,
        "payment_status": document.payment_status.value,
        "paid_amount": document.paid_amount,
        "remaining_amount": document.remaining_amount,
        "notes": document.notes,
        "order_number": document.order.order_number if document.order else None,
        "download_url": f"/api/v1/public/documents/{document.id}/pdf",
        "can_pay": document.type == DocumentType.FACTURE and document.remaining_amount > 0,
        "items": [
            {
                "product_name": item.product_name,
                "product_sku": item.product_sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_percent": item.discount_percent,
                "subtotal": item.subtotal
            }
            for item in document.items
        ],
        "client": {
            "name": client.company_name or f"{client.first_name} {client.last_name}",
            "type": client.type.value,
            "phone": client.phone,
            "email": client.email,
            "address": client.address
        }
    }


@router.get("/documents/{document_id}/pdf")
async def download_document_pdf(
    document_id: UUID,
    verification: str = Query(..., description="Phone or email for verification"),
    db: Session = Depends(get_db)
):
    """
    Download document PDF - PUBLIC endpoint with verification
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document introuvable"
        )
    
    client = document.client
    
    # Verify access
    verification_clean = verification.strip().lower()
    if verification_clean not in [(client.phone or "").strip().lower(), (client.email or "").strip().lower()]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès non autorisé"
        )
    
    if not document.pdf_path or not os.path.exists(document.pdf_path):
        # Generate PDF on the fly
        pdf_generator = TunisianPDFGenerator()
        
        # Convert to dicts
        doc_dict = {
            "id": document.id,
            "document_number": document.document_number,
            "status": document.status,
            "issue_date": document.issue_date,
            "due_date": document.due_date,
            "accepted_date": document.accepted_date,
            "subtotal": document.subtotal,
            "tax_amount": document.tax_amount,
            "discount": document.discount,
            "shipping_fee": document.shipping_fee,
            "total_amount": document.total_amount,
            "payment_status": document.payment_status,
            "paid_amount": document.paid_amount,
            "remaining_amount": document.remaining_amount,
            "notes": document.notes,
            "terms": document.terms
        }
        
        client_dict = {
            "id": client.id,
            "type": client.type.value,
            "company_name": client.company_name,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "fiscal_id": client.fiscal_id,
            "address": client.address,
            "phone": client.phone,
            "email": client.email
        }
        
        items_list = [
            {
                "product_name": item.product_name,
                "product_sku": item.product_sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_percent": item.discount_percent,
                "tax_percent": item.tax_percent,
                "subtotal": item.subtotal
            }
            for item in document.items
        ]
        
        try:
            if document.type == DocumentType.DEVIS:
                pdf_path = pdf_generator.generate_devis_pdf(
                    devis=doc_dict,
                    client=client_dict,
                    items=items_list
                )
            elif document.type == DocumentType.FACTURE:
                payments_list = [
                    {
                        "amount": payment.amount,
                        "payment_method": payment.payment_method,
                        "payment_date": payment.payment_date,
                        "reference_number": payment.reference_number,
                        "notes": payment.notes
                    }
                    for payment in document.payments
                ]
                
                pdf_path = pdf_generator.generate_facture_pdf(
                    facture=doc_dict,
                    client=client_dict,
                    items=items_list,
                    payments=payments_list
                )
            else:
                pdf_path = pdf_generator.generate_avoir_pdf(
                    avoir=doc_dict,
                    client=client_dict,
                    items=items_list
                )
            
            document.pdf_path = pdf_path
            db.commit()
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la génération du PDF: {str(e)}"
            )
    
    # Return PDF file
    from fastapi.responses import FileResponse
    return FileResponse(
        document.pdf_path,
        media_type='application/pdf',
        filename=f"{document.document_number}.pdf"
    )


# ============================================================================
# TRACKING ENDPOINT - Check order status without full verification
# ============================================================================

@router.get("/track/{order_number}")
async def track_order(
    order_number: str,
    db: Session = Depends(get_db)
):
    """
    Quick order status check - No sensitive data exposed
    """
    order = db.query(Order).filter(Order.order_number == order_number).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )
    
    # Return only non-sensitive tracking info
    return {
        "order_number": order.order_number,
        "status": order.status.value,
        "status_label": {
            "en_attente": "En attente de traitement",
            "en_traitement": "En cours de traitement",
            "confirme": "Confirmée",
            "annule": "Annulée"
        }.get(order.status.value, order.status.value),
        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        "total_items": len(order.items),
        "has_documents": len(order.documents) > 0,
        "message": "Pour accéder aux détails complets, veuillez vérifier votre commande avec votre numéro de téléphone ou email."
    }