from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas import schemas
from app.crud import crud

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@router.post("/", response_model=schemas.Supplier, status_code=status.HTTP_201_CREATED)
def create_new_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db)):
    db_supplier = crud.get_supplier_by_name(db, name=supplier.name)
    if db_supplier:
        raise HTTPException(
            status_code=400, detail="Supplier with this name already exists"
        )
    return crud.create_supplier(db=db, supplier=supplier)

@router.get("/", response_model=List[schemas.Supplier])
def read_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_suppliers(db, skip=skip, limit=limit)

@router.get("/{supplier_id}", response_model=schemas.Supplier)
def read_supplier(supplier_id: int, db: Session = Depends(get_db)):
    db_supplier = crud.get_supplier(db, supplier_id=supplier_id)
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return db_supplier

@router.put("/{supplier_id}", response_model=schemas.Supplier)
def update_supplier_details(
    supplier_id: int, supplier: schemas.SupplierUpdate, db: Session = Depends(get_db)
):
    db_supplier = crud.update_supplier(db=db, supplier_id=supplier_id, supplier_update=supplier)
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return db_supplier

@router.delete("/{supplier_id}")
def delete_supplier_record(supplier_id: int, db: Session = Depends(get_db)):
    db_supplier = crud.delete_supplier(db=db, supplier_id=supplier_id)
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"detail": "Supplier deleted successfully"}
