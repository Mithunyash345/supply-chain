from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import check_role
from app.schemas.financier import FinancierResponse, FinancierUpdate, FinancierBase

router = APIRouter(prefix="/financiers", tags=["Financiers"])

@router.get("/profile", response_model=FinancierResponse)
def get_financier_profile(
    current_user: models.User = Depends(check_role(["financier"])),
    db: Session = Depends(get_db)
):
    """
    Get the logged-in financier's profile configuration.
    """
    profile = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Financier profile not found.")
    return profile

@router.post("/profile", response_model=FinancierResponse, status_code=status.HTTP_201_CREATED)
def create_financier_profile(
    profile_in: FinancierBase,
    current_user: models.User = Depends(check_role(["financier"])),
    db: Session = Depends(get_db)
):
    """
    Initialize or overwrite the financier's profile configuration.
    """
    profile = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
    if profile:
        # If exists, update
        for field, value in profile_in.model_dump().items():
            setattr(profile, field, value)
    else:
        # Create new
        profile = models.Financier(
            user_id=current_user.id,
            **profile_in.model_dump()
        )
        db.add(profile)
        
    db.commit()
    db.refresh(profile)
    return profile

@router.put("/profile", response_model=FinancierResponse)
def update_financier_profile(
    profile_update: FinancierUpdate,
    current_user: models.User = Depends(check_role(["financier"])),
    db: Session = Depends(get_db)
):
    """
    Update part of the financier's profile configuration.
    """
    profile = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Financier profile not found.")
        
    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    db.commit()
    db.refresh(profile)
    return profile
