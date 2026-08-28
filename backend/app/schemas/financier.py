from pydantic import BaseModel, Field
from typing import Optional, List
import datetime

class FinancierBase(BaseModel):
    company_name: str
    financier_type: str
    available_capital: float = 0.0
    maximum_financing: float = 0.0
    risk_appetite: str = Field("medium", description="Risk appetite: low, medium, high")
    minimum_rate: float = Field(0.0, description="Minimum interest rate percentage")
    maximum_rate: float = Field(0.0, description="Maximum interest rate percentage")
    preferred_min_tenure: int = Field(30, description="Preferred minimum tenure in days")
    preferred_max_tenure: int = Field(120, description="Preferred maximum tenure in days")
    settlement_speed_hours: int = Field(24, description="Settlement speed in hours")
    preferred_industries: str = Field("", description="Comma-separated industries")

class FinancierCreate(FinancierBase):
    user_id: int

class FinancierUpdate(BaseModel):
    company_name: Optional[str] = None
    financier_type: Optional[str] = None
    available_capital: Optional[float] = None
    maximum_financing: Optional[float] = None
    risk_appetite: Optional[str] = None
    minimum_rate: Optional[float] = None
    maximum_rate: Optional[float] = None
    preferred_min_tenure: Optional[int] = None
    preferred_max_tenure: Optional[int] = None
    settlement_speed_hours: Optional[int] = None
    preferred_industries: Optional[str] = None

class FinancierResponse(FinancierBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True
