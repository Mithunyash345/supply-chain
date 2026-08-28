import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, UniqueConstraint, Text, Date
from sqlalchemy.orm import relationship
from app.database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # supplier, buyer, financier, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="user", uselist=False, cascade="all, delete-orphan")
    buyer = relationship("Buyer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    financier = relationship("Financier", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_name = Column(String, nullable=False)
    business_identifier = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="supplier", cascade="all, delete-orphan")


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_name = Column(String, nullable=False)
    business_identifier = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="buyer")
    purchase_orders = relationship("PurchaseOrder", back_populates="buyer", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="buyer", cascade="all, delete-orphan")
    verifications = relationship("InvoiceVerification", back_populates="buyer", cascade="all, delete-orphan")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, unique=True, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    buyer = relationship("Buyer", back_populates="purchase_orders")
    invoices = relationship("Invoice", back_populates="purchase_order")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id", ondelete="CASCADE"), nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    document_path = Column(String, nullable=True)
    extracted_text = Column(Text, nullable=True)
    verification_status = Column(String, default="pending")  # pending, under_review, verified, rejected
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)  # LOW, MEDIUM, HIGH
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Prevent duplicate invoice numbers for the same supplier
    __table_args__ = (
        UniqueConstraint("invoice_number", "supplier_id", name="uq_invoice_supplier"),
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="invoices")
    buyer = relationship("Buyer", back_populates="invoices")
    purchase_order = relationship("PurchaseOrder", back_populates="invoices")
    verification = relationship("InvoiceVerification", back_populates="invoice", uselist=False, cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="invoice", cascade="all, delete-orphan")
    offers = relationship("FinancierOffer", back_populates="invoice", cascade="all, delete-orphan")
    transaction = relationship("Transaction", back_populates="invoice", uselist=False, cascade="all, delete-orphan")


class InvoiceVerification(Base):
    __tablename__ = "invoice_verifications"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, unique=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id", ondelete="CASCADE"), nullable=False)
    document_check = Column(Boolean, default=False)
    database_check = Column(Boolean, default=False)
    duplicate_check = Column(Boolean, default=False)
    po_match_check = Column(Boolean, default=False)
    buyer_confirmation = Column(Boolean, default=False)
    buyer_comment = Column(String, nullable=True)
    verification_score = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending, verified, rejected
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="verification")
    buyer = relationship("Buyer", back_populates="verifications")


class Financier(Base):
    __tablename__ = "financiers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_name = Column(String, nullable=False)
    financier_type = Column(String, nullable=False)  # Bank, NBFC, Private Fund, etc.
    available_capital = Column(Float, default=0.0)
    maximum_financing = Column(Float, default=0.0)
    risk_appetite = Column(String, default="medium")  # low, medium, high
    minimum_rate = Column(Float, default=0.0)  # interest rate %
    maximum_rate = Column(Float, default=0.0)
    preferred_min_tenure = Column(Integer, default=30)  # days
    preferred_max_tenure = Column(Integer, default=120)  # days
    settlement_speed_hours = Column(Integer, default=24)
    preferred_industries = Column(String, default="")  # comma separated list
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="financier")
    matches = relationship("Match", back_populates="financier", cascade="all, delete-orphan")
    offers = relationship("FinancierOffer", back_populates="financier", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="financier", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    financier_id = Column(Integer, ForeignKey("financiers.id", ondelete="CASCADE"), nullable=False)
    eligibility_status = Column(Boolean, default=False)
    suitability_score = Column(Float, default=0.0)
    match_reasons = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="matches")
    financier = relationship("Financier", back_populates="matches")


class FinancierOffer(Base):
    __tablename__ = "financier_offers"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    financier_id = Column(Integer, ForeignKey("financiers.id", ondelete="CASCADE"), nullable=False)
    financing_amount = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)  # e.g., 8.5 for 8.5%
    fee = Column(Float, default=0.0)
    tenure_days = Column(Integer, nullable=False)
    settlement_speed_hours = Column(Integer, nullable=False)
    offer_score = Column(Float, default=0.0)
    status = Column(String, default="submitted")  # submitted, ranked, accepted, rejected, expired
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    invoice = relationship("Invoice", back_populates="offers")
    financier = relationship("Financier", back_populates="offers")
    transactions = relationship("Transaction", back_populates="offer", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, unique=True)
    financier_id = Column(Integer, ForeignKey("financiers.id", ondelete="CASCADE"), nullable=False)
    offer_id = Column(Integer, ForeignKey("financier_offers.id", ondelete="CASCADE"), nullable=False, unique=True)
    financed_amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, approved, funded, awaiting_settlement, settled, delayed, disputed
    funded_at = Column(DateTime, nullable=True)
    settlement_due_date = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Outcome / Learning Fields
    payment_on_time = Column(Boolean, nullable=True)
    delay_duration_days = Column(Integer, nullable=True)
    dispute_status = Column(String, nullable=True)
    financing_outcome = Column(String, nullable=True)  # e.g. success, default, recovered
    financier_performance = Column(String, nullable=True)  # rating or comments

    # Relationships
    invoice = relationship("Invoice", back_populates="transaction")
    financier = relationship("Financier", back_populates="transactions")
    offer = relationship("FinancierOffer", back_populates="transactions")
