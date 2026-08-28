from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import get_current_user, check_role
from app.services.matching_service import run_matching_engine
from app.schemas.offer import MatchResponse
from typing import List

router = APIRouter(prefix="/matching", tags=["Matching"])

@router.post("/{invoice_id}", response_model=List[MatchResponse])
def run_invoice_matching(
    invoice_id: int,
    current_user: models.User = Depends(check_role(["supplier", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Triggers the matching engine for a verified invoice.
    Filters eligible financiers and computes suitability scores.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # If supplier, verify they own the invoice
    if current_user.role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to run matching for this invoice")

    return run_matching_engine(db, invoice_id)

@router.get("/{invoice_id}", response_model=List[MatchResponse])
def get_invoice_matches(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve ranked list of financiers matched to an invoice.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Access control
    role = current_user.role
    if role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view matching results for this invoice")
            
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="Not authorized to view matching results")
            
    elif role == "financier":
        # Financier can view matches if they are listed in the matches for this invoice
        financier = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
        if not financier:
            raise HTTPException(status_code=403, detail="Financier profile not found")
        
        matches = db.query(models.Match).filter(
            models.Match.invoice_id == invoice_id,
            models.Match.financier_id == financier.id
        ).all()
        return matches

    matches = db.query(models.Match).filter(
        models.Match.invoice_id == invoice_id
    ).order_by(models.Match.eligibility_status.desc(), models.Match.suitability_score.desc()).all()
    
    return matches
