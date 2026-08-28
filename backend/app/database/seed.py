import logging
from sqlalchemy.orm import Session
from app.database import models
from app.core import security
import datetime

logger = logging.getLogger("app.database.seed")

def seed_db(db: Session):
    """
    Seeds the database with test users, suppliers, buyers, financiers,
    purchase orders, and invoices for the hackathon demo.
    """
    # 1. Create Users
    demo_users = [
        {"name": "ABC Components (Supplier)", "email": "supplier@example.com", "role": "supplier", "password": "password123"},
        {"name": "XYZ Motors (Buyer)", "email": "buyer@example.com", "role": "buyer", "password": "password123"},
        {"name": "Alpha Capital (Financier)", "email": "financier1@example.com", "role": "financier", "password": "password123"},
        {"name": "Beta Finance (Financier)", "email": "financier2@example.com", "role": "financier", "password": "password123"},
        {"name": "Gamma Ventures (Financier)", "email": "financier3@example.com", "role": "financier", "password": "password123"},
        {"name": "Delta Debt (Financier)", "email": "financier4@example.com", "role": "financier", "password": "password123"},
        {"name": "Admin Portal", "email": "admin@example.com", "role": "admin", "password": "password123"},
    ]

    created_users = {}
    for user_info in demo_users:
        existing = db.query(models.User).filter(models.User.email == user_info["email"]).first()
        if not existing:
            user = models.User(
                name=user_info["name"],
                email=user_info["email"],
                role=user_info["role"],
                hashed_password=security.get_password_hash(user_info["password"])
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created_users[user_info["email"]] = user
            logger.info(f"Seeded user: {user.email}")
        else:
            created_users[user_info["email"]] = existing

    # 2. Create Supplier Profile
    supplier_user = created_users["supplier@example.com"]
    supplier = db.query(models.Supplier).filter(models.Supplier.user_id == supplier_user.id).first()
    if not supplier:
        supplier = models.Supplier(
            user_id=supplier_user.id,
            company_name="ABC Components Ltd",
            business_identifier="TAX-SUP-1111",
            industry="Manufacturing"
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        logger.info("Seeded Supplier profile.")

    # 3. Create Buyer Profile
    buyer_user = created_users["buyer@example.com"]
    buyer = db.query(models.Buyer).filter(models.Buyer.user_id == buyer_user.id).first()
    if not buyer:
        buyer = models.Buyer(
            user_id=buyer_user.id,
            company_name="XYZ Motors Corp",
            business_identifier="TAX-BUY-2222",
            industry="Automotive"
        )
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
        logger.info("Seeded Buyer profile.")

    # 4. Create Financier Profiles
    # Financier 1: Alpha Capital (Low risk, large capital, lower rates, slow speed)
    f1_user = created_users["financier1@example.com"]
    f1 = db.query(models.Financier).filter(models.Financier.user_id == f1_user.id).first()
    if not f1:
        f1 = models.Financier(
            user_id=f1_user.id,
            company_name="Alpha Capital",
            financier_type="Bank",
            available_capital=50000000.0,
            maximum_financing=10000000.0,
            risk_appetite="low",
            minimum_rate=5.5,
            maximum_rate=9.0,
            preferred_min_tenure=30,
            preferred_max_tenure=90,
            settlement_speed_hours=24,
            preferred_industries="Automotive, Manufacturing"
        )
        db.add(f1)

    # Financier 2: Beta Finance (Medium risk, moderate capital, medium rates, fast speed)
    f2_user = created_users["financier2@example.com"]
    f2 = db.query(models.Financier).filter(models.Financier.user_id == f2_user.id).first()
    if not f2:
        f2 = models.Financier(
            user_id=f2_user.id,
            company_name="Beta Finance",
            financier_type="NBFC",
            available_capital=20000000.0,
            maximum_financing=5000000.0,
            risk_appetite="medium",
            minimum_rate=8.0,
            maximum_rate=14.0,
            preferred_min_tenure=15,
            preferred_max_tenure=120,
            settlement_speed_hours=12,
            preferred_industries="Automotive, Technology"
        )
        db.add(f2)

    # Financier 3: Gamma Ventures (High risk, lower capital, high rates, ultra-fast speed)
    f3_user = created_users["financier3@example.com"]
    f3 = db.query(models.Financier).filter(models.Financier.user_id == f3_user.id).first()
    if not f3:
        f3 = models.Financier(
            user_id=f3_user.id,
            company_name="Gamma Ventures",
            financier_type="Private Fund",
            available_capital=10000000.0,
            maximum_financing=2000000.0,
            risk_appetite="high",
            minimum_rate=12.0,
            maximum_rate=18.0,
            preferred_min_tenure=30,
            preferred_max_tenure=180,
            settlement_speed_hours=6,
            preferred_industries=""
        )
        db.add(f3)

    # Financier 4: Delta Debt (Low risk, medium capital, moderate rates, slow speed)
    f4_user = created_users["financier4@example.com"]
    f4 = db.query(models.Financier).filter(models.Financier.user_id == f4_user.id).first()
    if not f4:
        f4 = models.Financier(
            user_id=f4_user.id,
            company_name="Delta Debt",
            financier_type="NBFC",
            available_capital=30000000.0,
            maximum_financing=8000000.0,
            risk_appetite="low",
            minimum_rate=6.5,
            maximum_rate=10.0,
            preferred_min_tenure=60,
            preferred_max_tenure=120,
            settlement_speed_hours=48,
            preferred_industries="Manufacturing"
        )
        db.add(f4)
    
    db.commit()
    logger.info("Seeded 4 Financier profiles.")

    # 5. Create Purchase Orders
    po = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.po_number == "PO-1001").first()
    if not po:
        po = models.PurchaseOrder(
            po_number="PO-1001",
            supplier_id=supplier.id,
            buyer_id=buyer.id,
            amount=1000000.0,
            description="Purchase order for automotive component sub-assembly.",
            status="active"
        )
        db.add(po)
        db.commit()
        db.refresh(po)
        logger.info("Seeded Purchase Order PO-1001.")

    # 6. Pre-seed a few completed Transactions to create risk history for the AI engine
    # Invoice 1: Past invoice paid on time
    inv_past1 = db.query(models.Invoice).filter(models.Invoice.invoice_number == "INV-800").first()
    if not inv_past1:
        inv_past1 = models.Invoice(
            invoice_number="INV-800",
            supplier_id=supplier.id,
            buyer_id=buyer.id,
            purchase_order_id=po.id,
            invoice_date=datetime.date.today() - datetime.timedelta(days=90),
            due_date=datetime.date.today() - datetime.timedelta(days=30),
            subtotal=500000.0,
            tax=0.0,
            total_amount=500000.0,
            verification_status="verified",
            risk_score=18.5,
            risk_level="LOW"
        )
        db.add(inv_past1)
        db.commit()
        db.refresh(inv_past1)
        
        # Settle verification
        ver1 = models.InvoiceVerification(
            invoice_id=inv_past1.id,
            buyer_id=buyer.id,
            document_check=True,
            database_check=True,
            duplicate_check=True,
            po_match_check=True,
            buyer_confirmation=True,
            verification_score=100.0,
            status="verified",
            verified_at=datetime.datetime.utcnow() - datetime.timedelta(days=88)
        )
        db.add(ver1)
        
        # Create Offer
        off1 = models.FinancierOffer(
            invoice_id=inv_past1.id,
            financier_id=f1.id,
            financing_amount=450000.0,
            interest_rate=6.0,
            fee=500.0,
            tenure_days=60,
            settlement_speed_hours=24,
            offer_score=92.0,
            status="accepted"
        )
        db.add(off1)
        db.commit()
        db.refresh(off1)
        
        # Create transaction and settle it
        tx1 = models.Transaction(
            invoice_id=inv_past1.id,
            financier_id=f1.id,
            offer_id=off1.id,
            financed_amount=450000.0,
            status="settled",
            funded_at=datetime.datetime.utcnow() - datetime.timedelta(days=87),
            settlement_due_date=datetime.datetime.utcnow() - datetime.timedelta(days=27),
            settled_at=datetime.datetime.utcnow() - datetime.timedelta(days=28),
            payment_on_time=True,
            delay_duration_days=0,
            dispute_status="none",
            financing_outcome="success",
            financier_performance="excellent"
        )
        db.add(tx1)
        db.commit()
        logger.info("Seeded historical completed transaction (INV-800).")

    # Train risk model automatically using synthetic generator if not already present
    from app.ai import risk_model
    risk_model.train_model()
