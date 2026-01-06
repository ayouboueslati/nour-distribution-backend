from pydantic import BaseModel
from uuid import UUID

class StockAdjustmentRequest(BaseModel):
    product_id: UUID
    real_quantity: int
    reason: str
