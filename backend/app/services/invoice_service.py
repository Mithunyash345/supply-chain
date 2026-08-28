import os
import logging
from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status
from app.database import models
from app.ai.invoice_ai import extract_invoice_data
from app.utils.helpers import validate_uploaded_file, get_safe_unique_filename
from app.core.config import settings

logger = logging.getLogger("app.services.invoice_service")

def create_invoice_from_upload(
    db: Session, 
    file: UploadFile, 
    buyer_id: int, 
    supplier_id: int,
    purchase_order_id: int = None
) -> models.Invoice:
    """
    Handles file validation, upload, OCR data extraction, duplicate checks,
    and saves the invoice to the database.
    """
    # 1. Validate file
    validate_uploaded_file(file)
    
    # 2. Save file to uploads folder
    safe_filename = get_safe_unique_filename(file.filename)
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        logger.error(f"Failed to write uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded file."
        )

    # 3. Perform OCR & data extraction
    try:
        ocr_data = extract_invoice_data(file_path)
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        ocr_data = {
            "invoice_number": f"INV-{date.today().strftime('%Y%m%d')}",
            "invoice_date": date.today(),
            "due_date": date.today(),
            "subtotal": 0.0,
            "tax": 0.0,
            "total_amount": 0.0,
            "extracted_text": "Failed to extract text."
        }

    invoice_num = ocr_data.get("invoice_number") or f"INV-{date.today().strftime('%Y%m%d')}"
    
    # 4. Check for duplicate invoice numbers for this supplier
    existing_invoice = db.query(models.Invoice).filter(
        models.Invoice.invoice_number == invoice_num,
        models.Invoice.supplier_id == supplier_id
    ).first()
    
    if existing_invoice:
        # Clean up file
        try:
            os.remove(file_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "success": False,
                "message": "Invoice has already been submitted",
                "error_code": "DUPLICATE_INVOICE"
            }
        )

    # 5. Create invoice record
    # If a PO ID was not provided but OCR found a PO number, try to match it
    po_id = purchase_order_id
    if not po_id and ocr_data.get("purchase_order_number"):
        po_num = ocr_data["purchase_order_number"]
        po_match = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.po_number == po_num,
            models.PurchaseOrder.supplier_id == supplier_id,
            models.PurchaseOrder.buyer_id == buyer_id
        ).first()
        if po_match:
            po_id = po_match.id

    invoice = models.Invoice(
        invoice_number=invoice_num,
        supplier_id=supplier_id,
        buyer_id=buyer_id,
        purchase_order_id=po_id,
        invoice_date=ocr_data.get("invoice_date") or date.today(),
        due_date=ocr_data.get("due_date") or (date.today()),
        subtotal=ocr_data.get("subtotal") or 0.0,
        tax=ocr_data.get("tax") or 0.0,
        total_amount=ocr_data.get("total_amount") or 0.0,
        document_path=file_path,
        extracted_text=ocr_data.get("extracted_text"),
        verification_status="pending",
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # 6. Run initial verification checks
    from app.services.verification_service import run_initial_verification
    run_initial_verification(db, invoice.id)
    
    db.refresh(invoice)
    return invoice
