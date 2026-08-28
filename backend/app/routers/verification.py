from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import get_current_user, check_role
from app.schemas.invoice import InvoiceVerificationResponse
from app.services.verification_service import buyer_confirm_invoice
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/verification", tags=["Verification"])

class BuyerConfirmationComment(BaseModel):
    comment: Optional[str] = None

@router.get("/{invoice_id}", response_model=InvoiceVerificationResponse)
def get_invoice_verification_details(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve verification results and checks for a specific invoice.
    """
    verification = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.invoice_id == invoice_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification record not found for this invoice.")

    # Access control check
    role = current_user.role
    if role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or verification.invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view these verification details.")
            
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or verification.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="Not authorized to view these verification details.")

    return verification

@router.post("/{invoice_id}/approve", response_model=InvoiceVerificationResponse)
def approve_verification(
    invoice_id: int,
    comment_in: Optional[BuyerConfirmationComment] = None,
    current_user: models.User = Depends(check_role(["buyer"])),
    db: Session = Depends(get_db)
):
    """
    Approve an invoice verification (Buyer action).
    Once approved, the status is set to 'verified' and it is unlocked for risk analysis and matching.
    """
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found.")
        
    verification = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.invoice_id == invoice_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification record not found.")
        
    if verification.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="You do not have permission to approve this invoice.")

    comment = comment_in.comment if comment_in else None
    return buyer_confirm_invoice(db, invoice_id, buyer.id, approve=True, comment=comment)

@router.post("/{invoice_id}/reject", response_model=InvoiceVerificationResponse)
def reject_verification(
    invoice_id: int,
    comment_in: Optional[BuyerConfirmationComment] = None,
    current_user: models.User = Depends(check_role(["buyer"])),
    db: Session = Depends(get_db)
):
    """
    Reject an invoice verification (Buyer action).
    Stops the invoice from moving forward into financing.
    """
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found.")
        
    verification = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.invoice_id == invoice_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification record not found.")
        
    if verification.buyer_id != buyer.id:
        raise HTTPException(status_code=403, detail="You do not have permission to reject this invoice.")

    comment = comment_in.comment if comment_in else None
    return buyer_confirm_invoice(db, invoice_id, buyer.id, approve=False, comment=comment)
