import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database import models
from app.schemas.offer import OfferCreate
from app.ai.matching_ai import evaluate_and_rank_offers

logger = logging.getLogger("app.services.offer_service")

def submit_financier_offer(db: Session, financier_id: int, offer_in: OfferCreate) -> models.FinancierOffer:
    """
    Submits a financier offer for a verified invoice and recalculates offer rankings.
    """
    # 1. Fetch invoice and verify state
    invoice = db.query(models.Invoice).filter(models.Invoice.id == offer_in.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.verification_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offers can only be submitted for verified invoices."
        )

    # 2. Check if transaction already exists
    if invoice.transaction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invoice has already been financed/funded."
        )

    # 3. Save the new offer
    offer = models.FinancierOffer(
        invoice_id=offer_in.invoice_id,
        financier_id=financier_id,
        financing_amount=offer_in.financing_amount,
        interest_rate=offer_in.interest_rate,
        fee=offer_in.fee,
        tenure_days=offer_in.tenure_days,
        settlement_speed_hours=offer_in.settlement_speed_hours,
        status="submitted"
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    # 4. Fetch all offers for this invoice and run matching_ai evaluation to rank them
    all_offers = db.query(models.FinancierOffer).filter(
        models.FinancierOffer.invoice_id == invoice.id,
        models.FinancierOffer.status.in_(["submitted", "ranked"])
    ).all()
    
    offers_list = []
    for o in all_offers:
        offers_list.append({
            "id": o.id,
            "financing_amount": o.financing_amount,
            "interest_rate": o.interest_rate,
            "fee": o.fee,
            "tenure_days": o.tenure_days,
            "settlement_speed_hours": o.settlement_speed_hours
        })

    # Call AI offer evaluation ranking
    ranked_offers = evaluate_and_rank_offers(
        invoice_amount=invoice.total_amount,
        risk_level=invoice.risk_level or "MEDIUM",
        offers=offers_list
    )

    # Update scores in database
    for ro in ranked_offers:
        o_db = db.query(models.FinancierOffer).filter(models.FinancierOffer.id == ro["id"]).first()
        if o_db:
            o_db.offer_score = ro["offer_score"]
            o_db.status = "ranked"
            
    db.commit()
    db.refresh(offer)
    return offer

def accept_financier_offer(db: Session, offer_id: int, supplier_id: int) -> models.Transaction:
    """
    Accepts a financier offer, marks other offers as rejected,
    and initiates the financing transaction.
    """
    offer = db.query(models.FinancierOffer).filter(models.FinancierOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    invoice = db.query(models.Invoice).filter(models.Invoice.id == offer.invoice_id).first()
    
    # Verify ownership: Only the supplier of this invoice can accept an offer
    if invoice.supplier_id != supplier_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to accept offers for this invoice."
        )

    if offer.status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer is already accepted."
        )

    # Reject/close competing offers
    competing_offers = db.query(models.FinancierOffer).filter(
        models.FinancierOffer.invoice_id == invoice.id,
        models.FinancierOffer.id != offer.id
    ).all()
    for co in competing_offers:
        co.status = "rejected"

    offer.status = "accepted"

    # Create Transaction record
    transaction = models.Transaction(
        invoice_id=invoice.id,
        financier_id=offer.financier_id,
        offer_id=offer.id,
        financed_amount=offer.financing_amount,
        status="approved"
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    logger.info(f"Offer {offer.id} accepted. Transaction {transaction.id} created with status 'approved'.")
    return transaction
