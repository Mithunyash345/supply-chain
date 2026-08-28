import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.core import security
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login-form")

# Helper to retrieve current user based on JWT
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    email = security.decode_access_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Helper to check active status and role permissions
def check_role(required_roles: list[str]):
    def dependency(current_user: models.User = Depends(get_current_user)):
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. Access limited to: {', '.join(required_roles)}."
            )
        return current_user
    return dependency

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user and automatically initializes the role profile table
    (Supplier, Buyer, or Financier).
    """
    # Check if user already exists
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
        
    role = user_in.role.lower()
    if role not in ["supplier", "buyer", "financier", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'supplier', 'buyer', 'financier', or 'admin'."
        )

    # Create user
    user = models.User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create associated profile record
    if role == "supplier":
        supplier = models.Supplier(
            user_id=user.id,
            company_name=user.name,
            business_identifier=f"TAX-{user.id:04d}",
            industry="Manufacturing"
        )
        db.add(supplier)
    elif role == "buyer":
        buyer = models.Buyer(
            user_id=user.id,
            company_name=user.name,
            business_identifier=f"TAX-{user.id:04d}",
            industry="Automotive"
        )
        db.add(buyer)
    elif role == "financier":
        financier = models.Financier(
            user_id=user.id,
            company_name=user.name,
            financier_type="NBFC",
            available_capital=10000000.0,
            maximum_financing=2000000.0,
            risk_appetite="medium",
            minimum_rate=8.5,
            maximum_rate=15.0,
            preferred_min_tenure=30,
            preferred_max_tenure=120,
            settlement_speed_hours=24,
            preferred_industries="Automotive, Manufacturing"
        )
        db.add(financier)
        
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    Log in with email and password (JSON format).
    """
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not security.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# Standard OAuth2 form-data endpoint so Swagger UI Authorize button works
from fastapi.security import OAuth2PasswordRequestForm
@router.post("/login-form", include_in_schema=False)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    """
    Get current logged-in user profile.
    """
    return current_user
