from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import models
from app.database.database import get_db
from app.routers.auth import check_role
from app.schemas.invoice import InvoiceResponse
from typing import List, Dict, Any

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@router.get("/dashboard", response_model=Dict[str, Any])
def get_supplier_dashboard(
    current_user: models.User = Depends(check_role(["supplier"])),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics for the logged-in supplier.
    """
    supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier profile not found")

    invoices = db.query(models.Invoice).filter(models.Invoice.supplier_id == supplier.id).all()
    
    total_invoices_count = len(invoices)
    total_invoice_amount = sum(inv.total_amount for inv in invoices)
    
    # Funded transaction details
    funded_txs = db.query(models.Transaction).join(models.Invoice).filter(
        models.Invoice.supplier_id == supplier.id,
        models.Transaction.status == "funded"
    ).all()
    total_funded_amount = sum(tx.financed_amount for tx in funded_txs)
    
    # Count of statuses
    status_counts = {"pending": 0, "under_review": 0, "verified": 0, "rejected": 0}
    for inv in invoices:
        status_counts[inv.verification_status] = status_counts.get(inv.verification_status, 0) + 1
        
    # Active offers count
    active_offers_count = db.query(models.FinancierOffer).join(models.Invoice).filter(
        models.Invoice.supplier_id == supplier.id,
        models.FinancierOffer.status.in_(["submitted", "ranked"])
    ).count()

    return {
        "company_name": supplier.company_name,
        "business_identifier": supplier.business_identifier,
        "industry": supplier.industry,
        "metrics": {
            "total_invoices": total_invoices_count,
            "total_invoice_amount": total_invoice_amount,
            "total_financed_amount": total_funded_amount,
            "active_offers_count": active_offers_count,
            "status_counts": status_counts
        }
    }

@router.get("/invoices", response_model=List[InvoiceResponse])
def get_supplier_invoices(
    current_user: models.User = Depends(check_role(["supplier"])),
    db: Session = Depends(get_db)
):
    """
    Retrieve all invoices uploaded by the logged-in supplier.
    """
    supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier profile not found")
        
    invoices = db.query(models.Invoice).filter(models.Invoice.supplier_id == supplier.id).all()
    return invoices
