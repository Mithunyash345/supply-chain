from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import get_current_user, check_role
from app.schemas.invoice import InvoiceResponse, InvoiceDetailResponse
from app.services.invoice_service import create_invoice_from_upload
from typing import List, Optional

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.post("/upload", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def upload_invoice(
    buyer_id: int = Form(...),
    purchase_order_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: models.User = Depends(check_role(["supplier"])),
    db: Session = Depends(get_db)
):
    """
    Upload an invoice (PDF, PNG, JPG/JPEG).
    Only authenticated suppliers can upload invoices.
    """
    supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier profile not found")

    # Verify buyer exists
    buyer = db.query(models.Buyer).filter(models.Buyer.id == buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer profile not found")

    return create_invoice_from_upload(
        db=db,
        file=file,
        buyer_id=buyer_id,
        supplier_id=supplier.id,
        purchase_order_id=purchase_order_id
    )

@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
def get_invoice_by_id(
    invoice_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a single invoice, including its verification status.
    Requires relevant role access.
    """
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Role-based access control
    role = current_user.role
    if role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
            
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this invoice")
            
    elif role == "financier":
        # Financiers can view the invoice details if it is verified, or if they have matched/bid on it
        if invoice.verification_status != "verified":
            # Check if they have an offer
            financier = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
            if not financier:
                raise HTTPException(status_code=403, detail="Financier profile not found")
            has_offer = db.query(models.FinancierOffer).filter(
                models.FinancierOffer.invoice_id == invoice.id,
                models.FinancierOffer.financier_id == financier.id
            ).first()
            if not has_offer:
                raise HTTPException(status_code=403, detail="Not authorized to view unverified invoice")

    return invoice

@router.get("", response_model=List[InvoiceResponse])
def get_all_invoices(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List invoices based on user role:
    - Admin: All invoices.
    - Supplier: Uploaded invoices.
    - Buyer: Received invoices.
    - Financier: All verified invoices available in the marketplace.
    """
    role = current_user.role
    
    if role == "admin":
        return db.query(models.Invoice).all()
        
    elif role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier:
            return []
        return db.query(models.Invoice).filter(models.Invoice.supplier_id == supplier.id).all()
        
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer:
            return []
        return db.query(models.Invoice).filter(models.Invoice.buyer_id == buyer.id).all()
        
    elif role == "financier":
        # Financiers see verified invoices which are ready for financing
        return db.query(models.Invoice).filter(models.Invoice.verification_status == "verified").all()
        
    return []
