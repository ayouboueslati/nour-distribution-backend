from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.client import Client, ClientType
from app.schemas.client import ClientCreate, ClientUpdate
from app.services.base import BaseService

class ClientService(BaseService[Client]):
    def __init__(self, db: Session):
        super().__init__(Client, db)
    
    def create_client(self, client_data: ClientCreate) -> Client:
        """Create a new client with validation"""
        # Check if phone already exists
        existing_client = self.db.query(Client).filter(
            Client.phone == client_data.phone
        ).first()
        
        if existing_client:
            raise ValueError(f"Client with phone '{client_data.phone}' already exists")
        
        # Check if email exists (if provided)
        if client_data.email:
            existing_email = self.db.query(Client).filter(
                Client.email == client_data.email
            ).first()
            if existing_email:
                raise ValueError(f"Client with email '{client_data.email}' already exists")
        
        # Validate B2B specific fields
        if client_data.type == ClientType.B2B:
            if not client_data.company_name:
                raise ValueError("Company name is required for B2B clients")
        
        # Validate B2C specific fields
        if client_data.type == ClientType.B2C:
            if not client_data.first_name or not client_data.last_name:
                raise ValueError("First name and last name are required for B2C clients")
        
        return self.create(client_data.model_dump())
    
    def update_client(self, client_id: UUID, client_data: ClientUpdate) -> Optional[Client]:
        """Update client with validation"""
        client = self.get_by_id(client_id)
        if not client:
            return None
        
        update_data = client_data.model_dump(exclude_unset=True)
        
        # Check phone uniqueness if being updated
        if 'phone' in update_data and update_data['phone'] != client.phone:
            existing_phone = self.db.query(Client).filter(
                and_(
                    Client.phone == update_data['phone'],
                    Client.id != client_id
                )
            ).first()
            if existing_phone:
                raise ValueError(f"Client with phone '{update_data['phone']}' already exists")
        
        # Check email uniqueness if being updated
        if 'email' in update_data and update_data['email'] != client.email:
            existing_email = self.db.query(Client).filter(
                and_(
                    Client.email == update_data['email'],
                    Client.id != client_id
                )
            ).first()
            if existing_email:
                raise ValueError(f"Client with email '{update_data['email']}' already exists")
        
        return self.update(client, update_data)
    
    def search_clients(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Client]:
        """Search clients by name, email, phone, or company"""
        search_filter = or_(
            Client.company_name.ilike(f"%{search_term}%"),
            Client.contact_name.ilike(f"%{search_term}%"),
            Client.email.ilike(f"%{search_term}%"),
            Client.phone.ilike(f"%{search_term}%"),
            Client.first_name.ilike(f"%{search_term}%"),
            Client.last_name.ilike(f"%{search_term}%")
        )
        
        return self.db.query(Client).filter(search_filter).offset(skip).limit(limit).all()
    
    def get_active_clients(self, skip: int = 0, limit: int = 100) -> List[Client]:
        """Get only active clients"""
        return self.db.query(Client).filter(
            Client.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_clients_by_type(self, client_type: ClientType, skip: int = 0, limit: int = 100) -> List[Client]:
        """Get clients filtered by type (B2B or B2C)"""
        return self.db.query(Client).filter(
            Client.type == client_type
        ).offset(skip).limit(limit).all()
    
    def get_client_stats(self, client_id: UUID) -> Dict[str, Any]:
        """Get statistics for a client"""
        from app.models.order import Order
        from app.models.document import Document, DocumentType
        
        client = self.get_by_id(client_id)
        if not client:
            raise ValueError("Client not found")
        
        # Count orders
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.client_id == client_id
        ).scalar()
        
        # Count documents
        total_devis = self.db.query(func.count(Document.id)).filter(
            and_(
                Document.client_id == client_id,
                Document.type == DocumentType.DEVIS
            )
        ).scalar()
        
        total_factures = self.db.query(func.count(Document.id)).filter(
            and_(
                Document.client_id == client_id,
                Document.type == DocumentType.FACTURE
            )
        ).scalar()
        
        # Calculate total revenue
        total_revenue = self.db.query(func.sum(Document.total_amount)).filter(
            and_(
                Document.client_id == client_id,
                Document.type == DocumentType.FACTURE
            )
        ).scalar() or 0.0
        
        # Calculate outstanding amount
        outstanding_amount = self.db.query(func.sum(Document.remaining_amount)).filter(
            and_(
                Document.client_id == client_id,
                Document.type == DocumentType.FACTURE
            )
        ).scalar() or 0.0
        
        return {
            "client": client,
            "total_orders": total_orders,
            "total_devis": total_devis,
            "total_factures": total_factures,
            "total_revenue": float(total_revenue),
            "outstanding_amount": float(outstanding_amount)
        }