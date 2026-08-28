from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import get_current_user, check_role
from app.services.risk_service import calculate_invoice_risk
from typing import Dict, Any

router = APIRouter(prefix="/risk", tags=["Risk"])

@router.post("/{invoice_id}/calculate", response_model=Dict[str, Any])
def run_risk_calculation(
    invoice_id: int,
    current_user: models.User = Depends(check_role(["supplier", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Trigger risk analysis for a verified invoice.
    Updates the risk score and risk level in the database.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.verification_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk can only be calculated for verified invoices."
        )

    # If user is supplier, check ownership
    if current_user.role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to run risk for this invoice")

    updated_invoice = calculate_invoice_risk(db, invoice_id)
    
    return {
        "invoice_id": updated_invoice.id,
        "invoice_number": updated_invoice.invoice_number,
        "risk_score": updated_invoice.risk_score,
        "risk_level": updated_invoice.risk_level,
        "total_amount": updated_invoice.total_amount
    }

@router.get("/{invoice_id}", response_model=Dict[str, Any])
def get_invoice_risk(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current risk parameters and rating for a specific invoice.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Access control
    role = current_user.role
    if role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view risk for this invoice")
            
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="Not authorized to view risk for this invoice")

    if invoice.risk_score is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk score has not been calculated yet. Call POST /risk/{invoice_id}/calculate first."
        )

    # Standard explanation
    return {
        "invoice_id": invoice.id,
        "risk_score": invoice.risk_score,
        "risk_level": invoice.risk_level,
        "explanation": f"The invoice risk is assessed as {invoice.risk_level} based on historical delays and default counters."
    }
