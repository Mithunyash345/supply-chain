from pydantic import BaseModel, Field
from typing import Optional
import datetime

class TransactionBase(BaseModel):
    invoice_id: int
    financier_id: int
    offer_id: int
    financed_amount: float
    status: str

class TransactionResponse(TransactionBase):
    id: int
    funded_at: Optional[datetime.datetime] = None
    settlement_due_date: Optional[datetime.datetime] = None
    settled_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    
    # Outcome/Learning fields
    payment_on_time: Optional[bool] = None
    delay_duration_days: Optional[int] = None
    dispute_status: Optional[str] = None
    financing_outcome: Optional[str] = None
    financier_performance: Optional[str] = None

    class Config:
        from_attributes = True

class TransactionSettle(BaseModel):
    payment_on_time: bool = Field(True, description="Whether the payment was made on time")
    delay_duration_days: int = Field(0, description="Delay duration in days")
    dispute_status: Optional[str] = Field("none", description="Dispute status: none, resolved, ongoing")
    financing_outcome: str = Field("success", description="Outcome of financing: success, default, recovered")
    financier_performance: Optional[str] = Field("excellent", description="Rating/comments on financier's performance")
