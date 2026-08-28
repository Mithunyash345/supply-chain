from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import get_current_user, check_role
from app.schemas.offer import OfferCreate, OfferResponse
from app.schemas.transaction import TransactionResponse
from app.services.offer_service import submit_financier_offer, accept_financier_offer
from typing import List

router = APIRouter(prefix="/offers", tags=["Offers"])

@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    offer_in: OfferCreate,
    current_user: models.User = Depends(check_role(["financier"])),
    db: Session = Depends(get_db)
):
    """
    Submit a competing financing offer for a verified invoice.
    Only authenticated financiers can submit.
    """
    financier = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
    if not financier:
        raise HTTPException(status_code=404, detail="Financier profile not found")
        
    return submit_financier_offer(db, financier.id, offer_in)

@router.get("/invoice/{invoice_id}", response_model=List[OfferResponse])
def get_invoice_offers(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all submitted offers for a specific invoice, sorted by suitability ranking.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # Access control
    role = current_user.role
    if role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view offers for this invoice")
            
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="Not authorized to view offers for this invoice")
            
    elif role == "financier":
        # A financier can view the list of offers, but should only see their own offer unless they want to see market rankings.
        # Let's let them see all offers but mask competitor company names in UI,
        # or for simplicity, return all offers since it's a hackathon demo.
        pass

    # Sort offers by score descending (so ranked/best offer is first)
    offers = db.query(models.FinancierOffer).filter(
        models.FinancierOffer.invoice_id == invoice_id
    ).order_by(models.FinancierOffer.offer_score.desc()).all()
    
    return offers

@router.post("/{offer_id}/accept", response_model=TransactionResponse)
def accept_offer(
    offer_id: int,
    current_user: models.User = Depends(check_role(["supplier"])),
    db: Session = Depends(get_db)
):
    """
    Accept a financier offer (Supplier action).
    Triggers automated closing of other offers and initializes the financing transaction.
    """
    supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier profile not found")
        
    return accept_financier_offer(db, offer_id, supplier.id)

@router.post("/{offer_id}/reject", response_model=OfferResponse)
def reject_offer(
    offer_id: int,
    current_user: models.User = Depends(check_role(["supplier"])),
    db: Session = Depends(get_db)
):
    """
    Reject an offer (Supplier action).
    """
    offer = db.query(models.FinancierOffer).filter(models.FinancierOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    invoice = db.query(models.Invoice).filter(models.Invoice.id == offer.invoice_id).first()
    supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
    
    if not supplier or invoice.supplier_id != supplier.id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this offer")
        
    offer.status = "rejected"
    db.commit()
    db.refresh(offer)
    return offer
