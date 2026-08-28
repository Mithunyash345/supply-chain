import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.database import Base, get_db
from app.database import models

# Use a separate test database file
TEST_DATABASE_URL = "sqlite:///./test_supply_chain.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Pre-populate required test records
    db = TestingSessionLocal()
    
    # Ensure tables are clean
    db.query(models.User).delete()
    db.query(models.Supplier).delete()
    db.query(models.Buyer).delete()
    db.query(models.PurchaseOrder).delete()
    db.query(models.Invoice).delete()
    db.query(models.InvoiceVerification).delete()
    db.query(models.Financier).delete()
    db.query(models.FinancierOffer).delete()
    db.query(models.Transaction).delete()
    db.commit()
    db.close()
    
    yield
    
    # Tear down database file after tests
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_supply_chain.db"):
        try:
            os.remove("./test_supply_chain.db")
        except PermissionError:
            pass

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "supply-chain-financing-backend"
    }

def test_auth_registration_and_login():
    # 1. Register Supplier
    response = client.post("/auth/register", json={
        "name": "Test Supplier Corp",
        "email": "test_supplier@example.com",
        "password": "password123",
        "role": "supplier"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test_supplier@example.com"
    
    # 2. Register Buyer
    response = client.post("/auth/register", json={
        "name": "Test Buyer Corp",
        "email": "test_buyer@example.com",
        "password": "password123",
        "role": "buyer"
    })
    assert response.status_code == 201
    
    # 3. Register Financier
    response = client.post("/auth/register", json={
        "name": "Test Financier Capital",
        "email": "test_financier@example.com",
        "password": "password123",
        "role": "financier"
    })
    assert response.status_code == 201

    # 4. Login Supplier
    login_resp = client.post("/auth/login", json={
        "email": "test_supplier@example.com",
        "password": "password123"
    })
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    
    # 5. Read current user details
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    me_resp = client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "test_supplier@example.com"

def test_invoice_upload_and_verification_flow():
    # Log in supplier
    sup_login = client.post("/auth/login", json={
        "email": "test_supplier@example.com",
        "password": "password123"
    })
    sup_token = sup_login.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # Fetch supplier profile id
    db = TestingSessionLocal()
    supplier = db.query(models.Supplier).first()
    buyer = db.query(models.Buyer).first()
    
    # Create a matching PO in database
    po = models.PurchaseOrder(
        po_number="PO-TEST-100",
        supplier_id=supplier.id,
        buyer_id=buyer.id,
        amount=500000.0,
        status="active"
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    
    # Create test text file to mimic PDF/image upload
    with open("test_invoice.pdf", "w") as f:
        f.write("Invoice Number: INV-TEST-100\nPurchase Order: PO-TEST-100\nTotal Amount: 500000.00\n")

    # Upload Invoice
    with open("test_invoice.pdf", "rb") as f:
        upload_resp = client.post(
            "/invoices/upload",
            headers=sup_headers,
            data={"buyer_id": buyer.id, "purchase_order_id": po.id},
            files={"file": ("test_invoice.pdf", f, "application/pdf")}
        )
    
    # Clean up local file
    if os.path.exists("test_invoice.pdf"):
        os.remove("test_invoice.pdf")

    assert upload_resp.status_code == 201
    invoice_data = upload_resp.json()
    assert invoice_data["invoice_number"] == "INV-TEST-100"
    assert invoice_data["verification_status"] == "under_review"

    # Duplicate Invoice Detection
    with open("test_invoice_dup.pdf", "w") as f:
        f.write("Invoice Number: INV-TEST-100\nTotal Amount: 500000.00\n")
    
    with open("test_invoice_dup.pdf", "rb") as f:
        dup_resp = client.post(
            "/invoices/upload",
            headers=sup_headers,
            data={"buyer_id": buyer.id},
            files={"file": ("test_invoice.pdf", f, "application/pdf")}
        )
    if os.path.exists("test_invoice_dup.pdf"):
        os.remove("test_invoice_dup.pdf")
        
    assert dup_resp.status_code == 409  # Conflict - duplicate invoice

    # Verify Invoice (Buyer Action)
    # Log in buyer
    buyer_login = client.post("/auth/login", json={
        "email": "test_buyer@example.com",
        "password": "password123"
    })
    buyer_token = buyer_login.json()["access_token"]
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

    # Retrieve verifications list
    ver_list_resp = client.get("/buyers/verifications", headers=buyer_headers)
    assert ver_list_resp.status_code == 200
    assert len(ver_list_resp.json()) >= 1

    # Approve verification
    approve_resp = client.post(
        f"/verification/{invoice_data['id']}/approve",
        headers=buyer_headers,
        json={"comment": "Verified and accepted."}
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "verified"

def test_risk_and_matching_flow():
    # Log in supplier
    sup_login = client.post("/auth/login", json={
        "email": "test_supplier@example.com",
        "password": "password123"
    })
    sup_headers = {"Authorization": f"Bearer {sup_login.json()['access_token']}"}

    db = TestingSessionLocal()
    invoice = db.query(models.Invoice).first()
    db.close()

    # Trigger risk calculation
    risk_resp = client.post(f"/risk/{invoice.id}/calculate", headers=sup_headers)
    assert risk_resp.status_code == 200
    assert "risk_score" in risk_resp.json()

    # Trigger matching
    matching_resp = client.post(f"/matching/{invoice.id}", headers=sup_headers)
    assert matching_resp.status_code == 200
    assert len(matching_resp.json()) >= 1
    assert matching_resp.json()[0]["eligibility_status"] is True

def test_offers_and_transactions_lifecycle():
    # Log in financier
    fin_login = client.post("/auth/login", json={
        "email": "test_financier@example.com",
        "password": "password123"
    })
    fin_token = fin_login.json()["access_token"]
    fin_headers = {"Authorization": f"Bearer {fin_token}"}

    db = TestingSessionLocal()
    invoice = db.query(models.Invoice).first()
    db.close()

    # Submit offer
    offer_resp = client.post(
        "/offers",
        headers=fin_headers,
        json={
            "invoice_id": invoice.id,
            "financing_amount": 450000.0,
            "interest_rate": 7.5,
            "fee": 1000.0,
            "tenure_days": 60,
            "settlement_speed_hours": 12
        }
    )
    assert offer_resp.status_code == 201
    offer_data = offer_resp.json()
    assert offer_data["status"] == "ranked"

    # Log in supplier to accept offer
    sup_login = client.post("/auth/login", json={
        "email": "test_supplier@example.com",
        "password": "password123"
    })
    sup_headers = {"Authorization": f"Bearer {sup_login.json()['access_token']}"}

    # Accept offer
    accept_resp = client.post(f"/offers/{offer_data['id']}/accept", headers=sup_headers)
    assert accept_resp.status_code == 200
    tx_data = accept_resp.json()
    assert tx_data["status"] == "approved"

    # Financier funds the transaction
    fund_resp = client.post(f"/transactions/{tx_data['id']}/fund", headers=fin_headers)
    assert fund_resp.status_code == 200
    assert fund_resp.json()["status"] == "funded"

    # Log in buyer to settle transaction
    buyer_login = client.post("/auth/login", json={
        "email": "test_buyer@example.com",
        "password": "password123"
    })
    buyer_headers = {"Authorization": f"Bearer {buyer_login.json()['access_token']}"}

    # Settle transaction
    settle_resp = client.post(
        f"/transactions/{tx_data['id']}/settle",
        headers=buyer_headers,
        json={
            "payment_on_time": True,
            "delay_duration_days": 0,
            "dispute_status": "none",
            "financing_outcome": "success",
            "financier_performance": "excellent"
        }
    )
    assert settle_resp.status_code == 200
    assert settle_resp.json()["status"] == "settled"
