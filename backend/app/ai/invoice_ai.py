import os
import re
import logging
from datetime import date, datetime, timedelta

logger = logging.getLogger("app.ai.invoice_ai")

# Attempt to import PaddleOCR
PADDLEOCR_AVAILABLE = False
try:
    from paddleocr import PaddleOCR
    # Initialize PaddleOCR (this will download models on first run)
    ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    PADDLEOCR_AVAILABLE = True
    logger.info("PaddleOCR loaded successfully.")
except Exception as e:
    logger.warning(f"PaddleOCR not available, running in mock/fallback mode. Error: {e}")
    ocr = None

def extract_invoice_data(file_path: str) -> dict:
    """
    Extracts structured invoice data from the document.
    Attempts to use PaddleOCR first. If unavailable, falls back to a text/regex/mock parser.
    """
    extracted_text = ""
    structured_data = {
        "invoice_number": None,
        "supplier_name": None,
        "buyer_name": None,
        "invoice_date": None,
        "due_date": None,
        "purchase_order_number": None,
        "subtotal": None,
        "tax": None,
        "total_amount": None,
    }

    if PADDLEOCR_AVAILABLE and ocr is not None:
        try:
            # Check if file exists and has image extension for OCR
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg"]:
                result = ocr.ocr(file_path, cls=True)
                text_lines = []
                if result and result[0]:
                    for line in result[0]:
                        text_lines.append(line[1][0])
                extracted_text = "\n".join(text_lines)
                logger.info("Text extracted using PaddleOCR.")
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {e}. Falling back to mock parser.")

    # Fallback to Text/Regex/Mock parsing
    if not extracted_text:
        # Check if we can read the file as text (e.g. if it's a mock pdf/txt upload)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1000)
                # If it looks like text, use it
                if any(k in content.lower() for k in ["invoice", "inv-", "po-", "total", "amount"]):
                    extracted_text = content
        except Exception:
            pass

    # If still no text or it's a binary file, create mock extracted text for the hackathon
    if not extracted_text:
        # Generate some mock text mimicking an invoice layout
        filename = os.path.basename(file_path)
        
        # We can extract invoice number suggestions from filename if present
        inv_match = re.search(r"inv[-_]?(\d+)", filename, re.IGNORECASE)
        inv_num = f"INV-{inv_match.group(1)}" if inv_match else "INV-1001"
        
        po_match = re.search(r"po[-_]?(\d+)", filename, re.IGNORECASE)
        po_num = f"PO-{po_match.group(1)}" if po_match else "PO-1001"

        extracted_text = f"""
        INVOICE
        Invoice Number: {inv_num}
        Supplier: ABC Components Ltd
        Buyer: XYZ Motors Corp
        Purchase Order: {po_num}
        Invoice Date: {date.today().isoformat()}
        Due Date: {(date.today() + timedelta(days=60)).isoformat()}
        
        Description: Auto Parts Supply
        Subtotal: 1000000.00
        Tax (18%): 180000.00
        Total Amount: 1180000.00
        """
        logger.info("Generated synthetic invoice text for fallback parser.")

    # Parse extracted text using RegEx
    structured_data["extracted_text"] = extracted_text

    # Helper regex patterns
    inv_num_pattern = r"(?:Invoice\s*Number|Inv\s*#|Invoice\s*No\.?)\s*:\s*([A-Z0-9-]+)"
    po_num_pattern = r"(?:Purchase\s*Order|PO\s*#|PO\s*No\.?)\s*:\s*([A-Z0-9-]+)"
    subtotal_pattern = r"(?:Subtotal|Sub-Total|Net\s*Amount)\s*:\s*([\d,]+\.?\d*)"
    tax_pattern = r"(?:Tax|GST|VAT)\s*(?:\(\d+%\))?\s*:\s*([\d,]+\.?\d*)"
    total_pattern = r"(?:Total\s*Amount|Total|Grand\s*Total|Amount\s*Due)\s*:\s*([\d,]+\.?\d*)"
    
    # Run regex search
    inv_match = re.search(inv_num_pattern, extracted_text, re.IGNORECASE)
    if inv_match:
        structured_data["invoice_number"] = inv_match.group(1).strip()
        
    po_match = re.search(po_num_pattern, extracted_text, re.IGNORECASE)
    if po_match:
        structured_data["purchase_order_number"] = po_match.group(1).strip()

    sub_match = re.search(subtotal_pattern, extracted_text, re.IGNORECASE)
    if sub_match:
        try:
            structured_data["subtotal"] = float(sub_match.group(1).replace(",", ""))
        except ValueError:
            pass

    tax_match = re.search(tax_pattern, extracted_text, re.IGNORECASE)
    if tax_match:
        try:
            structured_data["tax"] = float(tax_match.group(1).replace(",", ""))
        except ValueError:
            pass

    tot_match = re.search(total_pattern, extracted_text, re.IGNORECASE)
    if tot_match:
        try:
            structured_data["total_amount"] = float(tot_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Extract dates
    date_patterns = [
        r"Invoice\s*Date\s*:\s*([\d-]{10})",
        r"Due\s*Date\s*:\s*([\d-]{10})"
    ]
    for i, pattern in enumerate(date_patterns):
        match = re.search(pattern, extracted_text, re.IGNORECASE)
        if match:
            try:
                dt = datetime.strptime(match.group(1).strip(), "%Y-%m-%d").date()
                if i == 0:
                    structured_data["invoice_date"] = dt
                else:
                    structured_data["due_date"] = dt
            except ValueError:
                pass

    # Fallback default values for demo flow if fields were not parsed
    if not structured_data["invoice_number"]:
        structured_data["invoice_number"] = "INV-1001"
    if not structured_data["invoice_date"]:
        structured_data["invoice_date"] = date.today()
    if not structured_data["due_date"]:
        structured_data["due_date"] = date.today() + timedelta(days=60)
    if not structured_data["total_amount"]:
        structured_data["total_amount"] = 1180000.00
    if not structured_data["subtotal"]:
        structured_data["subtotal"] = structured_data["total_amount"] - (structured_data["tax"] or 0.0)
    if not structured_data["tax"]:
        structured_data["tax"] = 0.0
    
    # Attempt to extract names (very basic mock logic for hackathon demo)
    if "ABC Components" in extracted_text or "abc" in extracted_text.lower():
        structured_data["supplier_name"] = "ABC Components"
    if "XYZ Motors" in extracted_text or "xyz" in extracted_text.lower():
        structured_data["buyer_name"] = "XYZ Motors"

    return structured_data
