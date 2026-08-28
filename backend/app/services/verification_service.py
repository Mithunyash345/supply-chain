import datetime
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database import models

logger = logging.getLogger("app.services.verification_service")

def run_initial_verification(db: Session, invoice_id: int) -> models.InvoiceVerification:
    """
    Runs deterministic verification checks:
    1. Document Check
    2. Database Check
    3. Duplicate Check
    4. PO Match Check
    
    Generates a verification score. Updates status to 'under_review'.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # CHECK 1: DOCUMENT CHECK
    # Check that required fields exist, amounts are valid, dates make sense.
    document_check = True
    doc_reasons = []
    if not invoice.invoice_number:
        document_check = False
        doc_reasons.append("Missing invoice number.")
    if invoice.total_amount <= 0:
        document_check = False
        doc_reasons.append("Invalid total amount (must be > 0).")
    if invoice.invoice_date and invoice.due_date:
        if invoice.due_date < invoice.invoice_date:
            document_check = False
            doc_reasons.append("Due date is before invoice date.")
    else:
        document_check = False
        doc_reasons.append("Missing invoice or due date.")

    # CHECK 2: DATABASE CHECK
    # Check that supplier and buyer exist
    database_check = True
    db_reasons = []
    supplier = db.query(models.Supplier).filter(models.Supplier.id == invoice.supplier_id).first()
    buyer = db.query(models.Buyer).filter(models.Buyer.id == invoice.buyer_id).first()
    
    if not supplier:
        database_check = False
        db_reasons.append("Supplier record not found in database.")
    if not buyer:
        database_check = False
        db_reasons.append("Buyer record not found in database.")

    # CHECK 3: DUPLICATE CHECK
    # Check if this invoice number was already submitted by this supplier previously,
    # or if there is an active transaction for this invoice.
    duplicate_check = True
    dup_reasons = []
    
    # Already submitted check (excluding this record itself)
    dup_invs = db.query(models.Invoice).filter(
        models.Invoice.invoice_number == invoice.invoice_number,
        models.Invoice.supplier_id == invoice.supplier_id,
        models.Invoice.id != invoice.id
    ).all()
    if dup_invs:
        duplicate_check = False
        dup_reasons.append("Invoice number already exists for this supplier.")

    # Checked if already financed
    if invoice.transaction:
        duplicate_check = False
        dup_reasons.append("This invoice is already tied to an existing transaction.")

    # CHECK 4: PO MATCH CHECK
    po_match_check = False
    po_reasons = []
    if invoice.purchase_order_id:
        po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == invoice.purchase_order_id).first()
        if po:
            database_check = True  # Verified PO exists
            # Compare supplier, buyer, PO amount, and status
            if po.supplier_id != invoice.supplier_id:
                po_reasons.append("PO supplier does not match invoice supplier.")
            if po.buyer_id != invoice.buyer_id:
                po_reasons.append("PO buyer does not match invoice buyer.")
            if abs(po.amount - invoice.total_amount) > 0.01:
                po_reasons.append(f"PO amount ({po.amount}) does not match invoice amount ({invoice.total_amount}).")
            
            if not po_reasons:
                po_match_check = True
            else:
                po_match_check = False
        else:
            po_reasons.append("Linked Purchase Order ID not found.")
    else:
        # If no PO is linked, it's not a failure, but PO match check is false/neutral.
        # For security in supply chain finance, matching a PO is a strong trust builder.
        po_reasons.append("No Purchase Order linked to this invoice.")
        po_match_check = False

    # Calculate verification score (deterministic, max 100)
    # Weights: Document (25%), Database (25%), Duplicate Check (30%), PO Match (20%)
    score = 0.0
    if document_check: score += 25.0
    if database_check: score += 25.0
    if duplicate_check: score += 30.0
    if po_match_check: score += 20.0

    # Save verification state
    verification = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.invoice_id == invoice.id
    ).first()
    
    if not verification:
        verification = models.InvoiceVerification(
            invoice_id=invoice.id,
            buyer_id=invoice.buyer_id
        )
        db.add(verification)

    verification.document_check = document_check
    verification.database_check = database_check
    verification.duplicate_check = duplicate_check
    verification.po_match_check = po_match_check
    verification.verification_score = score
    
    # Check if verification requires human buyer confirmation to be fully "verified"
    if score >= 80.0:
        verification.status = "under_review"
        invoice.verification_status = "under_review"
    else:
        verification.status = "rejected"
        invoice.verification_status = "rejected"
        
    db.commit()
    db.refresh(verification)
    db.refresh(invoice)
    return verification

def buyer_confirm_invoice(
    db: Session, 
    invoice_id: int, 
    buyer_id: int, 
    approve: bool, 
    comment: str = None
) -> models.InvoiceVerification:
    """
    Updates invoice verification status based on buyer confirmation.
    If buyer rejects, status becomes 'rejected'. If buyer approves, status becomes 'verified'.
    """
    verification = db.query(models.InvoiceVerification).filter(
        models.InvoiceVerification.invoice_id == invoice_id,
        models.InvoiceVerification.buyer_id == buyer_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Invoice verification record not found")
        
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    
    if approve:
        # Check if the score is sufficient before allowing verification
        if verification.verification_score < 50.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice failed basic verification checks and cannot be approved."
            )
        verification.buyer_confirmation = True
        verification.status = "verified"
        verification.verification_score = min(100.0, verification.verification_score + 20.0) # Add final 20% for buyer sign-off
        invoice.verification_status = "verified"
    else:
        verification.buyer_confirmation = False
        verification.status = "rejected"
        invoice.verification_status = "rejected"
        
    verification.buyer_comment = comment
    verification.verified_at = datetime.datetime.utcnow()
    
    db.commit()
    db.refresh(verification)
    db.refresh(invoice)
    
    # If the invoice is verified, let's automatically run the risk assessment
    if invoice.verification_status == "verified":
        from app.services.risk_service import calculate_invoice_risk
        calculate_invoice_risk(db, invoice.id)
        
    return verification
