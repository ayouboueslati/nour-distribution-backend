from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from app.models.charge import Charge, ChargeCategory, ChargeType, ChargeRecurrence
from app.schemas.charge import ChargeCreate, ChargeUpdate

class ChargeService:
    def __init__(self, db: Session):
        self.db = db

    def get_charges(self, skip: int = 0, limit: int = 100) -> List[Charge]:
        return self.db.query(Charge).order_by(Charge.date.desc()).offset(skip).limit(limit).all()

    def get_charge(self, charge_id: UUID) -> Optional[Charge]:
        return self.db.query(Charge).filter(Charge.id == charge_id).first()

    def create_charge(self, charge_in: ChargeCreate) -> Charge:
        db_charge = Charge(
            description=charge_in.description,
            amount=charge_in.amount,
            category=charge_in.category,
            date=charge_in.date,
            type=charge_in.type,
            recurrence=charge_in.recurrence,
            validated=charge_in.validated,
            supplier=charge_in.supplier,
            receipt_number=charge_in.receipt_number,
            notes=charge_in.notes
        )
        self.db.add(db_charge)
        self.db.commit()
        self.db.refresh(db_charge)
        return db_charge

    def update_charge(self, charge_id: UUID, charge_in: ChargeUpdate) -> Optional[Charge]:
        db_charge = self.get_charge(charge_id)
        if not db_charge:
            return None
        
        update_data = charge_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_charge, field, value)
            
        self.db.commit()
        self.db.refresh(db_charge)
        return db_charge

    def delete_charge(self, charge_id: UUID) -> bool:
        db_charge = self.get_charge(charge_id)
        if not db_charge:
            return False
        
        self.db.delete(db_charge)
        self.db.commit()
        return True
