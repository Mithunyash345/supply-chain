import logging
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.database import models
from app.ai.risk_model import predict_risk

logger = logging.getLogger("app.services.risk_service")

def calculate_invoice_risk(db: Session, invoice_id: int) -> models.Invoice:
    """
    Gathers historical and contextual metrics for the supplier and buyer,
    runs the risk assessment engine (ML or Fallback), and updates the invoice record.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # 1. Gather Supplier metrics
    supplier_id = invoice.supplier_id
    
    # Total historical transactions for this supplier
    supplier_txs = db.query(models.Transaction).join(models.Invoice).filter(
        models.Invoice.supplier_id == supplier_id
    ).all()
    
    supplier_transaction_count = len(supplier_txs)
    
    # Delayed payments count
    supplier_delay_count = sum(1 for tx in supplier_txs if tx.delay_duration_days and tx.delay_duration_days > 0)
    
    # Default count
    previous_default_count = sum(1 for tx in supplier_txs if tx.financing_outcome == "default")

    # 2. Gather Buyer metrics
    buyer_id = invoice.buyer_id
    buyer_txs = db.query(models.Transaction).join(models.Invoice).filter(
        models.Invoice.buyer_id == buyer_id
    ).all()
    
    buyer_transaction_count = len(buyer_txs)
    
    # Buyer average delay
    buyer_delays = [tx.delay_duration_days for tx in buyer_txs if tx.delay_duration_days is not None]
    buyer_average_delay = float(sum(buyer_delays) / len(buyer_delays)) if buyer_delays else 0.0

    # 3. Calculate invoice tenure
    days_to_due = (invoice.due_date - invoice.invoice_date).days if invoice.invoice_date and invoice.due_date else 60
    if days_to_due <= 0:
        days_to_due = 60 # safe fallback

    # 4. Standard default values for a new transaction estimate
    # Financing amount is typically 90% of total amount
    financing_amount = invoice.total_amount * 0.90
    tenure_days = days_to_due

    # 5. Call ML Risk prediction
    prediction = predict_risk(
        invoice_amount=invoice.total_amount,
        days_to_due=days_to_due,
        supplier_transaction_count=supplier_transaction_count,
        supplier_delay_count=supplier_delay_count,
        buyer_transaction_count=buyer_transaction_count,
        buyer_average_delay=buyer_average_delay,
        previous_default_count=previous_default_count,
        financing_amount=financing_amount,
        tenure_days=tenure_days
    )

    # 6. Update invoice fields
    invoice.risk_score = prediction["risk_score"]
    invoice.risk_level = prediction["risk_level"]
    
    db.commit()
    db.refresh(invoice)
    
    logger.info(f"Risk calculated for Invoice {invoice.id}: Score={invoice.risk_score}, Level={invoice.risk_level}")
    return invoice
