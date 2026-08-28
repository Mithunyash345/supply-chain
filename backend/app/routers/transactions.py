import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import models
from app.database.database import get_db
from app.routers.auth import get_current_user, check_role
from app.schemas.transaction import TransactionResponse, TransactionSettle
from typing import List

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionResponse])
def list_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all transactions filtered by role:
    - Admin: All transactions.
    - Supplier: Transactions linked to their uploaded invoices.
    - Buyer: Transactions linked to their received invoices.
    - Financier: Transactions they have financed.
    """
    role = current_user.role
    
    if role == "admin":
        return db.query(models.Transaction).all()
        
    elif role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier:
            return []
        return db.query(models.Transaction).join(models.Invoice).filter(
            models.Invoice.supplier_id == supplier.id
        ).all()
        
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer:
            return []
        return db.query(models.Transaction).join(models.Invoice).filter(
            models.Invoice.buyer_id == buyer.id
        ).all()
        
    elif role == "financier":
        financier = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
        if not financier:
            return []
        return db.query(models.Transaction).filter(
            models.Transaction.financier_id == financier.id
        ).all()
        
    return []

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction_details(
    transaction_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed metrics of a specific funding transaction.
    """
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Access control check
    role = current_user.role
    if role == "supplier":
        supplier = db.query(models.Supplier).filter(models.Supplier.user_id == current_user.id).first()
        if not supplier or tx.invoice.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this transaction")
            
    elif role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or tx.invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this transaction")
            
    elif role == "financier":
        financier = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
        if not financier or tx.financier_id != financier.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this transaction")

    return tx

@router.post("/{transaction_id}/fund", response_model=TransactionResponse)
def fund_transaction(
    transaction_id: int,
    current_user: models.User = Depends(check_role(["financier", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Fund a transaction (Financier action).
    Changes status from 'approved' or 'pending' to 'funded' and record timestamp.
    """
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If financier, verify they are the funding provider
    if current_user.role == "financier":
        financier = db.query(models.Financier).filter(models.Financier.user_id == current_user.id).first()
        if not financier or tx.financier_id != financier.id:
            raise HTTPException(status_code=403, detail="You are not authorized to fund this transaction")

    if tx.status not in ["approved", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fund transaction in '{tx.status}' state."
        )

    tx.status = "funded"
    tx.funded_at = datetime.datetime.utcnow()
    
    # Calculate expected due date based on offer tenure
    tenure_days = tx.offer.tenure_days
    tx.settlement_due_date = tx.funded_at + datetime.timedelta(days=tenure_days)

    db.commit()
    db.refresh(tx)
    return tx

@router.post("/{transaction_id}/settle", response_model=TransactionResponse)
def settle_transaction(
    transaction_id: int,
    settle_in: TransactionSettle,
    current_user: models.User = Depends(check_role(["buyer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Settle the transaction (Buyer action, representing payment to the financier).
    Moves status to 'settled' and records settlement and default/delay parameters for AI model training.
    """
    tx = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify that the buyer is the payer
    if current_user.role == "buyer":
        buyer = db.query(models.Buyer).filter(models.Buyer.user_id == current_user.id).first()
        if not buyer or tx.invoice.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="You are not authorized to settle this transaction")

    if tx.status != "funded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot settle transaction that has not been funded (current status: '{tx.status}')."
        )

    tx.status = "settled"
    tx.settled_at = datetime.datetime.utcnow()
    
    # Store outcome for AI feedback loop
    tx.payment_on_time = settle_in.payment_on_time
    tx.delay_duration_days = settle_in.delay_duration_days
    tx.dispute_status = settle_in.dispute_status
    tx.financing_outcome = settle_in.financing_outcome
    tx.financier_performance = settle_in.financier_performance

    db.commit()
    db.refresh(tx)
    return tx
