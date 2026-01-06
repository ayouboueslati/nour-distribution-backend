from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import pandas as pd
from app.models.document import (
    DocumentType, 
    DocumentStatus, 
    PaymentStatus,

)

class PaymentTracker:
    """Comprehensive payment tracking system for offline payments"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_offline_payment(
        self, 
        facture_id: UUID, 
        amount: float, 
        payment_method: str,
        payment_date: datetime,
        reference_number: str,
        notes: str,
        recorded_by: UUID
    ) -> Dict:
        """Record an offline payment"""
        from app.models.document import Payment, Document, PaymentStatus
        
        facture = self.db.query(Document).filter(
            and_(
                Document.id == facture_id,
                Document.type == DocumentType.FACTURE
            )
        ).first()
        
        if not facture:
            raise ValueError("Facture not found")
        
        if amount > facture.remaining_amount:
            raise ValueError(f"Payment amount {amount} exceeds remaining {facture.remaining_amount}")
        
        # Create payment record
        payment = Payment(
            document_id=facture_id,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            reference_number=reference_number,
            notes=notes,
            recorded_by=recorded_by
        )
        self.db.add(payment)
        
        # Update facture payment status
        facture.paid_amount += amount
        facture.remaining_amount -= amount
        
        if facture.remaining_amount == 0:
            facture.payment_status = PaymentStatus.PAYE
            facture.status = DocumentStatus.PAYE
        elif facture.paid_amount > 0:
            facture.payment_status = PaymentStatus.PARTIEL
        
        # Check if payment is overdue
        if facture.due_date and facture.due_date < datetime.now(timezone.utc) and facture.remaining_amount > 0:
            facture.payment_status = PaymentStatus.EN_RETARD
        
        self.db.commit()
        
        return {
            "payment_id": payment.id,
            "facture_number": facture.document_number,
            "amount_paid": amount,
            "remaining_amount": facture.remaining_amount,
            "payment_status": facture.payment_status.value,
            "payment_date": payment_date
        }
    
    def get_payment_aging_report(self, client_id: Optional[UUID] = None) -> Dict:
        """Get payment aging report (Moroccan standard)"""
        from app.models.document import Document, DocumentType, PaymentStatus
        from app.models.client import Client
        
        query = self.db.query(Document, Client).join(
            Client, Document.client_id == Client.id
        ).filter(
            and_(
                Document.type == DocumentType.FACTURE,
                Document.remaining_amount > 0
            )
        )
        
        if client_id:
            query = query.filter(Document.client_id == client_id)
        
        factures = query.all()
        
        aging_buckets = {
            "current": [],      # 0-30 days
            "31_60": [],        # 31-60 days
            "61_90": [],        # 61-90 days
            "91_120": [],       # 91-120 days
            "over_120": []      # Over 120 days
        }
        
        today = datetime.now(timezone.utc).date()
        
        for facture, client in factures:
            due_date = facture.due_date.date() if facture.due_date else facture.issue_date.date() + timedelta(days=30)
            days_overdue = (today - due_date).days if today > due_date else 0
            
            aging_item = {
                "facture_id": facture.id,
                "facture_number": facture.document_number,
                "client_name": client.company_name or f"{client.first_name} {client.last_name}",
                "issue_date": facture.issue_date,
                "due_date": due_date,
                "total_amount": facture.total_amount,
                "paid_amount": facture.paid_amount,
                "remaining_amount": facture.remaining_amount,
                "days_overdue": days_overdue,
                "client_id": client.id
            }
            
            if days_overdue <= 30:
                aging_buckets["current"].append(aging_item)
            elif days_overdue <= 60:
                aging_buckets["31_60"].append(aging_item)
            elif days_overdue <= 90:
                aging_buckets["61_90"].append(aging_item)
            elif days_overdue <= 120:
                aging_buckets["91_120"].append(aging_item)
            else:
                aging_buckets["over_120"].append(aging_item)
        
        # Calculate totals
        totals = {}
        for bucket, items in aging_buckets.items():
            totals[bucket] = {
                "count": len(items),
                "total_amount": sum(item["remaining_amount"] for item in items),
                "oldest_days": max((item["days_overdue"] for item in items), default=0)
            }
        
        return {
            "aging_buckets": aging_buckets,
            "totals": totals,
            "summary": {
                "total_outstanding": sum(bucket["total_amount"] for bucket in totals.values()),
                "total_factures": sum(bucket["count"] for bucket in totals.values()),
                "weighted_average_days": sum(
                    bucket["total_amount"] * bucket["oldest_days"] 
                    for bucket in totals.values()
                ) / sum(bucket["total_amount"] for bucket in totals.values()) 
                if sum(bucket["total_amount"] for bucket in totals.values()) > 0 else 0
            },
            "generated_at": datetime.now(timezone.utc)
        }
    
    def generate_payment_reminders(self, days_before: int = 7) -> List[Dict]:
        """Generate payment reminders for upcoming due dates"""
        from app.models.document import Document, DocumentType
        
        reminder_date = datetime.now(timezone.utc).date() + timedelta(days=days_before)
        
        upcoming_factures = self.db.query(Document).filter(
            and_(
                Document.type == DocumentType.FACTURE,
                Document.remaining_amount > 0,
                func.date(Document.due_date) == reminder_date
            )
        ).all()
        
        reminders = []
        
        for facture in upcoming_factures:
            client = facture.client
            
            reminder = {
                "facture_id": facture.id,
                "facture_number": facture.document_number,
                "client_id": client.id,
                "client_name": client.company_name or f"{client.first_name} {client.last_name}",
                "client_email": client.email,
                "client_phone": client.phone,
                "due_date": facture.due_date,
                "remaining_amount": facture.remaining_amount,
                "total_amount": facture.total_amount,
                "days_until_due": days_before,
                "reminder_type": "upcoming_payment"
            }
            
            reminders.append(reminder)
        
        return reminders
    
    def get_client_payment_history(self, client_id: UUID) -> Dict:
        """Get complete payment history for a client"""
        from app.models.document import Document, Payment, DocumentType
        
        # Get all factures for client
        factures = self.db.query(Document).filter(
            and_(
                Document.client_id == client_id,
                Document.type == DocumentType.FACTURE
            )
        ).order_by(Document.issue_date.desc()).all()
        
        payment_history = []
        total_stats = {
            "total_factures": 0,
            "total_amount": 0,
            "total_paid": 0,
            "total_outstanding": 0,
            "on_time_payments": 0,
            "late_payments": 0
        }
        
        for facture in factures:
            payments = facture.payments
            
            facture_data = {
                "facture_id": facture.id,
                "facture_number": facture.document_number,
                "issue_date": facture.issue_date,
                "due_date": facture.due_date,
                "total_amount": facture.total_amount,
                "paid_amount": facture.paid_amount,
                "remaining_amount": facture.remaining_amount,
                "payment_status": facture.payment_status.value,
                "is_overdue": facture.payment_status == PaymentStatus.EN_RETARD,
                "payments": [
                    {
                        "payment_id": payment.id,
                        "amount": payment.amount,
                        "payment_method": payment.payment_method,
                        "payment_date": payment.payment_date,
                        "reference_number": payment.reference_number,
                        "notes": payment.notes,
                        "recorded_by": payment.recorded_by,
                        "days_after_issue": (payment.payment_date - facture.issue_date).days
                    }
                    for payment in payments
                ]
            }
            
            payment_history.append(facture_data)
            
            # Update stats
            total_stats["total_factures"] += 1
            total_stats["total_amount"] += facture.total_amount
            total_stats["total_paid"] += facture.paid_amount
            total_stats["total_outstanding"] += facture.remaining_amount
            
            if facture.payment_status == PaymentStatus.PAYE:
                # Check if paid on time
                last_payment = max(payments, key=lambda p: p.payment_date) if payments else None
                if last_payment and facture.due_date:
                    if last_payment.payment_date <= facture.due_date:
                        total_stats["on_time_payments"] += 1
                    else:
                        total_stats["late_payments"] += 1
        
        # Calculate payment behavior metrics
        if total_stats["total_factures"] > 0:
            total_stats["payment_ratio"] = total_stats["total_paid"] / total_stats["total_amount"]
            total_stats["on_time_ratio"] = total_stats["on_time_payments"] / total_stats["total_factures"]
        
        return {
            "payment_history": payment_history,
            "stats": total_stats,
            "client_id": client_id
        }
    
    def export_payment_report(self, start_date: datetime, end_date: datetime, format: str = "excel") -> str:
        """Export payment report in specified format"""
        from app.models.document import Document, Payment, DocumentType
        
        # Get all payments in date range
        payments = self.db.query(Payment).join(
            Document, Payment.document_id == Document.id
        ).filter(
            and_(
                Payment.payment_date.between(start_date, end_date),
                Document.type == DocumentType.FACTURE
            )
        ).all()
        
        # Prepare data
        data = []
        for payment in payments:
            data.append({
                "Date Paiement": payment.payment_date.strftime("%d/%m/%Y"),
                "N° Facture": payment.document.document_number,
                "Client": payment.document.client.company_name 
                    or f"{payment.document.client.first_name} {payment.document.client.last_name}",
                "Montant": payment.amount,
                "Méthode": payment.payment_method,
                "Référence": payment.reference_number or "",
                "Notes": payment.notes or "",
                "Enregistré par": payment.user.username if payment.user else "System"
            })
        
        df = pd.DataFrame(data)
        
        if format == "excel":
            filename = f"payment_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
            filepath = f"reports/{filename}"
            
            # Create directory if not exists
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Paiements', index=False)
                
                # Add summary sheet
                summary_data = {
                    "Total Paiements": [len(payments)],
                    "Total Montant": [df["Montant"].sum()],
                    "Premier Paiement": [df["Date Paiement"].min()],
                    "Dernier Paiement": [df["Date Paiement"].max()],
                    "Moyenne Paiement": [df["Montant"].mean()],
                    "Méthode la plus utilisée": [df["Méthode"].mode().iloc[0] if not df["Méthode"].mode().empty else ""]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Résumé', index=False)
            
            return filepath
        
        elif format == "csv":
            filename = f"payment_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            filepath = f"reports/{filename}"
            
            df.to_csv(filepath, index=False, sep=';', encoding='utf-8')
            return filepath
        
        else:
            raise ValueError(f"Unsupported format: {format}")