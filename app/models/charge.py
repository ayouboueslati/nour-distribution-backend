from sqlalchemy import Column, String, Text, Float, DateTime, Enum, Boolean
from .base import BaseModel
import enum

class ChargeCategory(str, enum.Enum):
    RENT = "rent"
    UTILITIES = "utilities"
    SALARIES = "salaries"
    MARKETING = "marketing"
    SUPPLIES = "supplies"
    MAINTENANCE = "maintenance"
    OTHER = "other"

class ChargeType(str, enum.Enum):
    FIXED = "fixed"
    VARIABLE = "variable"

class ChargeRecurrence(str, enum.Enum):
    PONCTUEL = "ponctuel"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class Charge(BaseModel):
    __tablename__ = "charges"
    
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(Enum(ChargeCategory, values_callable=lambda x: [e.value for e in x]), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # New fields to match frontend
    type = Column(Enum(ChargeType, values_callable=lambda x: [e.value for e in x]), default=ChargeType.VARIABLE)
    recurrence = Column(Enum(ChargeRecurrence, values_callable=lambda x: [e.value for e in x]), default=ChargeRecurrence.PONCTUEL)
    validated = Column(Boolean, default=False)
    supplier = Column(String(255))
    
    # Additional details
    receipt_number = Column(String(100))
    notes = Column(Text)
    
    def __repr__(self):
        return f"<Charge {self.description}: {self.amount} DT>"