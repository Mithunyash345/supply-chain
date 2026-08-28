from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import datetime

# Purchase Order Schemas
class PurchaseOrderBase(BaseModel):
    po_number: str
    amount: float
    description: Optional[str] = None
    status: str = "active"

class PurchaseOrderCreate(PurchaseOrderBase):
    supplier_id: int
    buyer_id: int

class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    supplier_id: int
    buyer_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Invoice Verification Schemas
class InvoiceVerificationResponse(BaseModel):
    id: int
    invoice_id: int
    buyer_id: int
    document_check: bool
    database_check: bool
    duplicate_check: bool
    po_match_check: bool
    buyer_confirmation: bool
    buyer_comment: Optional[str] = None
    verification_score: float
    status: str
    verified_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Invoice Schemas
class InvoiceBase(BaseModel):
    invoice_number: str
    invoice_date: datetime.date
    due_date: datetime.date
    subtotal: float
    tax: float = 0.0
    total_amount: float

class InvoiceCreate(InvoiceBase):
    buyer_id: int
    purchase_order_id: Optional[int] = None

class InvoiceResponse(InvoiceBase):
    id: int
    supplier_id: int
    buyer_id: int
    purchase_order_id: Optional[int] = None
    document_path: Optional[str] = None
    verification_status: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class InvoiceDetailResponse(InvoiceResponse):
    extracted_text: Optional[str] = None
    verification: Optional[InvoiceVerificationResponse] = None

    class Config:
        from_attributes = True
