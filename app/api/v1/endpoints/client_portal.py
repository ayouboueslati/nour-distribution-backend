from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import os
from app.core.database import get_db
from app.api.v1.deps import get_current_user
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.models.document import Document, DocumentType, DocumentStatus
from app.services.order_service import OrderService
from app.services.document_service import DocumentService
from app.services.pdf_generator import TunisianPDFGenerator

router = APIRouter()

@router.get("/me/orders", response_model=List[dict])
async def get_my_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_user)
):
    """Get current client's orders"""
    order_service = OrderService(db)
    
    query = db.query(Order).filter(Order.client_id == current_client.id)
    
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status.value,
            "submitted_at": order.submitted_at,
            "total_amount": order.total_amount,
            "items_count": len(order.items),
            "has_devis": any(doc.type == DocumentType.DEVIS for doc in order.documents),
            "has_facture": any(doc.type == DocumentType.FACTURE for doc in order.documents)
        }
        for order in orders
    ]

@router.get("/me/orders/{order_id}")
async def get_my_order_details(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client)
):
    """Get detailed order information"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.client_id == current_client.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Get related documents
    documents = db.query(Document).filter(
        Document.order_id == order_id,
        Document.client_id == current_client.id
    ).all()
    
    return {
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status.value,
            "submitted_at": order.submitted_at,
            "processed_at": order.processed_at,
            "confirmed_at": order.confirmed_at,
            "subtotal": order.subtotal,
            "shipping_fee": order.shipping_fee,
            "discount": order.discount,
            "tax_amount": order.tax_amount,
            "total_amount": order.total_amount,
            "shipping_address": order.shipping_address,
            "delivery_notes": order.delivery_notes,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else "Unknown",
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "subtotal": item.subtotal
                }
                for item in order.items
            ]
        },
        "documents": [
            {
                "id": doc.id,
                "type": doc.type.value,
                "document_number": doc.document_number,
                "status": doc.status.value,
                "issue_date": doc.issue_date,
                "due_date": doc.due_date,
                "total_amount": doc.total_amount,
                "payment_status": doc.payment_status.value,
                "paid_amount": doc.paid_amount,
                "remaining_amount": doc.remaining_amount,
                "pdf_url": f"/api/v1/client/documents/{doc.id}/pdf" if doc.pdf_path else None
            }
            for doc in documents
        ]
    }

@router.get("/me/documents")
async def get_my_documents(
    doc_type: Optional[str] = Query(None, description="devis, facture, or avoir"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client)
):
    """Get client's documents"""
    query = db.query(Document).filter(Document.client_id == current_client.id)
    
    if doc_type:
        try:
            type_enum = DocumentType(doc_type)
            query = query.filter(Document.type == type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type: {doc_type}"
            )
    
    documents = query.order_by(Document.issue_date.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": doc.id,
            "type": doc.type.value,
            "document_number": doc.document_number,
            "status": doc.status.value,
            "issue_date": doc.issue_date,
            "due_date": doc.due_date,
            "total_amount": doc.total_amount,
            "payment_status": doc.payment_status.value,
            "paid_amount": doc.paid_amount,
            "remaining_amount": doc.remaining_amount,
            "notes": doc.notes,
            "order_number": doc.order.order_number if doc.order else None,
            "download_url": f"/api/v1/client/documents/{doc.id}/pdf" if doc.pdf_path else None,
            "can_pay": doc.type == DocumentType.FACTURE and doc.remaining_amount > 0
        }
        for doc in documents
    ]

@router.get("/me/documents/{document_id}/pdf")
async def download_document_pdf(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client)
):
    """Download document PDF"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.client_id == current_client.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not document.pdf_path or not os.path.exists(document.pdf_path):
        # Generate PDF on the fly if not exists
        pdf_generator = TunisianPDFGenerator()
        
        if document.type == DocumentType.DEVIS:
            pdf_path = pdf_generator.generate_devis_pdf(
                devis=document,
                client=current_client,
                items=document.items
            )
        elif document.type == DocumentType.FACTURE:
            pdf_path = pdf_generator.generate_facture_pdf(
                facture=document,
                client=current_client,
                items=document.items,
                payments=document.payments
            )
        else:
            pdf_path = pdf_generator.generate_avoir_pdf(
                avoir=document,
                client=current_client,
                items=document.items
            )
        
        document.pdf_path = pdf_path
        db.commit()
    
    # Return PDF file
    from fastapi.responses import FileResponse
    return FileResponse(
        document.pdf_path,
        media_type='application/pdf',
        filename=f"{document.document_number}.pdf"
    )

@router.get("/me/stats")
async def get_my_stats(
    db: Session = Depends(get_db),
    current_client: Client = Depends(get_current_client)
):
    """Get client statistics"""
    from sqlalchemy import func
    
    # Order stats
    order_stats = db.query(
        func.count(Order.id).label('total_orders'),
        func.sum(Order.total_amount).label('total_spent'),
        func.avg(Order.total_amount).label('avg_order_value')
    ).filter(Order.client_id == current_client.id).first()
    
    # Document stats
    doc_stats = db.query(
        Document.type,
        func.count(Document.id).label('count'),
        func.sum(Document.total_amount).label('total_amount'),
        func.sum(Document.remaining_amount).label('remaining_amount')
    ).filter(
        Document.client_id == current_client.id,
        Document.type.in_([DocumentType.DEVIS, DocumentType.FACTURE])
    ).group_by(Document.type).all()
    
    # Payment stats
    payment_stats = db.query(
        func.sum(Document.paid_amount).label('total_paid'),
        func.sum(Document.remaining_amount).label('total_outstanding'),
        func.count(Document.id).label('pending_factures')
    ).filter(
        Document.client_id == current_client.id,
        Document.type == DocumentType.FACTURE,
        Document.remaining_amount > 0
    ).first()
    
    # Recent activity
    recent_orders = db.query(Order).filter(
        Order.client_id == current_client.id
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    recent_docs = db.query(Document).filter(
        Document.client_id == current_client.id
    ).order_by(Document.created_at.desc()).limit(5).all()
    
    return {
        "client": {
            "id": current_client.id,
            "name": current_client.company_name or f"{current_client.first_name} {current_client.last_name}",
            "type": current_client.type.value,
            "member_since": current_client.created_at.strftime("%Y-%m-%d")
        },
        "order_stats": {
            "total_orders": order_stats.total_orders or 0,
            "total_spent": float(order_stats.total_spent or 0),
            "avg_order_value": float(order_stats.avg_order_value or 0)
        },
        "document_stats": {
            doc_type.type.value: {
                "count": doc_type.count,
                "total_amount": float(doc_type.total_amount or 0),
                "remaining_amount": float(doc_type.remaining_amount or 0)
            }
            for doc_type in doc_stats
        },
        "payment_stats": {
            "total_paid": float(payment_stats.total_paid or 0),
            "total_outstanding": float(payment_stats.total_outstanding or 0),
            "pending_factures": payment_stats.pending_factures or 0
        },
        "recent_activity": {
            "orders": [
                {
                    "order_number": order.order_number,
                    "date": order.created_at.strftime("%Y-%m-%d"),
                    "status": order.status.value,
                    "amount": order.total_amount
                }
                for order in recent_orders
            ],
            "documents": [
                {
                    "type": doc.type.value,
                    "number": doc.document_number,
                    "date": doc.issue_date.strftime("%Y-%m-%d"),
                    "amount": doc.total_amount,
                    "status": doc.status.value
                }
                for doc in recent_docs
            ]
        }
    }