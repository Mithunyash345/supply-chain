from pydantic import BaseModel
from typing import Optional
import datetime

class BuyerBase(BaseModel):
    company_name: str
    business_identifier: str
    industry: str

class BuyerCreate(BuyerBase):
    user_id: int

class BuyerUpdate(BaseModel):
    company_name: Optional[str] = None
    business_identifier: Optional[str] = None
    industry: Optional[str] = None

class BuyerResponse(BuyerBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
