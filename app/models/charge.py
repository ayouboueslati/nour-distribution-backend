from sqlalchemy import Column, String, Text, Float, DateTime, Enum
from .base import BaseModel
import enum

class ChargeCategory(enum.Enum):
    RENT = "rent"
    UTILITIES = "utilities"
    SALARIES = "salaries"
    MARKETING = "marketing"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    OTHER = "other"

class Charge(BaseModel):
    __tablename__ = "charges"
    
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(Enum(ChargeCategory), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Additional details
    receipt_number = Column(String(100))
    notes = Column(Text)
    
    def __repr__(self):
        return f"<Charge {self.description}: {self.amount}€>"