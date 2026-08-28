import os
import re
import uuid
from fastapi import UploadFile, HTTPException, status


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

def validate_uploaded_file(file: UploadFile):
    """Validate uploaded file type and size"""
    # Check extension
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed extensions are: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check content type
    content_type = file.content_type
    if not content_type.startswith("image/") and content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Only PDF and images (PNG, JPEG) are allowed."
        )

def get_safe_unique_filename(filename: str) -> str:
    """Generate a safe, unique filename using UUID"""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    # Sanitize original name
    base_name = os.path.splitext(filename)[0]
    base_name = re.sub(r"[^a-zA-Z0-9_-]", "_", base_name)[:50]
    # Add unique identifier
    unique_id = uuid.uuid4().hex[:12]
    return f"{base_name}_{unique_id}.{ext}"
