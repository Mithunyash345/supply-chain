from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.database import models
from app.database.database import get_db
from app.routers.auth import check_role
from app.schemas.invoice import InvoiceResponse, InvoiceVerificationResponse
from app.services.verification_service import buyer_confirm_invoice

router = APIRouter(prefix="/buyers", tags=["Buyers"])

class Optional_Comment(BaseModel):
    comment: Optional[str] = None

@router.get("/dashboard", response_model=Dict[str, Any])
def get_buyer_dashboard(
    current_user: models.User = Depends(check_role(["buyer"])),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics for the logged-in buyer.
    """
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")

    invoices = db.query(models.Invoice).filter(models.Invoice.buyer_id == buyer.id).all()
    
    total_invoices_count = len(invoices)
    total_payable_amount = sum(inv.total_amount for inv in invoices if inv.verification_status != "rejected")
    
    # Active verifications
    pending_verifications = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.buyer_id == buyer.id,
        models.InvoiceVerification.status == "under_review"
    ).count()

    status_counts = {"pending": 0, "under_review": 0, "verified": 0, "rejected": 0}
    for inv in invoices:
        status_counts[inv.verification_status] = status_counts.get(inv.verification_status, 0) + 1

    return {
        "company_name": buyer.company_name,
        "business_identifier": buyer.business_identifier,
        "industry": buyer.industry,
        "metrics": {
            "total_invoices_received": total_invoices_count,
            "total_outstanding_payables": total_payable_amount,
            "pending_verifications_count": pending_verifications,
            "status_counts": status_counts
        }
    }

@router.get("/verifications", response_model=List[InvoiceVerificationResponse])
def get_buyer_verifications(
    current_user: models.User = Depends(check_role(["buyer"])),
    db: Session = Depends(get_db)
):
    """
    Retrieve all pending verification requests for this buyer.
    """
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")
        
    verifications = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.buyer_id == buyer.id,
        models.InvoiceVerification.status == "under_review"
    ).all()
    return verifications

@router.post("/invoices/{invoice_id}/approve", response_model=InvoiceVerificationResponse)
def approve_invoice_via_buyer(
    invoice_id: int,
    comment: Optional_Comment = None,
    current_user: models.User = Depends(check_role(["buyer"])),
    db: Session = Depends(get_db)
):
    """
    Confirm and verify an invoice (Buyer action).
    """
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")
        
    # Check that this invoice belongs to this buyer
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice or invoice.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="You do not have permission to approve this invoice.")
        
    comment_text = comment.comment if comment else None
    return buyer_confirm_invoice(db, invoice_id, buyer.id, approve=True, comment=comment_text)

@router.post("/invoices/{invoice_id}/reject", response_model=InvoiceVerificationResponse)
def reject_invoice_via_buyer(
    invoice_id: int,
    comment: Optional_Comment = None,
    current_user: models.User = Depends(check_role(["buyer"])),
    db: Session = Depends(get_db)
):
    """
    Reject an invoice (Buyer action).
    """
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")
        
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice or invoice.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="You do not have permission to reject this invoice.")
        
    comment_text = comment.comment if comment else None
    return buyer_confirm_invoice(db, invoice_id, buyer.id, approve=False, comment=comment_text)
