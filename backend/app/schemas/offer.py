from pydantic import BaseModel
from typing import Optional
import datetime

class OfferBase(BaseModel):
    invoice_id: int
    financing_amount: float
    interest_rate: float
    fee: float = 0.0
    tenure_days: int
    settlement_speed_hours: int

class OfferCreate(OfferBase):
    pass

class OfferResponse(OfferBase):
    id: int
    financier_id: int
    offer_score: float
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class MatchResponse(BaseModel):
    id: int
    invoice_id: int
    financier_id: int
    eligibility_status: bool
    suitability_score: float
    match_reasons: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True
