# AI-Powered Supply-Chain Financing Marketplace Backend

This is a complete, clean, modular backend for an AI-Powered Supply-Chain Financing Marketplace prototype designed for hackathons. It is built using Python, FastAPI, SQLAlchemy, and Scikit-Learn.

The marketplace workflow enables Suppliers to upload invoices, which are parsed via OCR, verified, assessed for risk using a machine learning model, matched with eligible Financiers, and put out for competitive bidding. Financiers submit competing offers which are ranked using a multi-factor matching engine. Suppliers accept offers, and the transaction is funded and settled.

---

## 1. Architecture

The backend follows a modular layered architecture:

```
backend/
├── app/
│   ├── core/           # Configuration, Security tokens
│   ├── database/       # SQLAlchemy models, seed script, session manager
│   ├── schemas/        # Pydantic schemas (request/response validation)
│   ├── routers/        # FastAPI endpoints split by role/entity
│   ├── services/       # Core business logic (verification, matching, etc.)
│   ├── ai/             # OCR, risk prediction model, multi-factor offer scoring
│   └── utils/          # File upload and validation helpers
```

---

## 2. Technology Stack

* **Python 3.10+**
* **FastAPI**: Modern, fast web framework
* **Uvicorn**: ASGI server
* **SQLAlchemy 2.x**: Database ORM
* **SQLite / PostgreSQL**: Database storage (SQLite is used out-of-the-box, but PostgreSQL can be configured)
* **Pydantic / Pydantic Settings**: Data validation and settings management
* **python-jose / bcrypt**: Token authentication and password hashing
* **PaddleOCR**: Optical Character Recognition for invoice reading (with text-regex fallback)
* **Scikit-Learn**: RandomForest Classifier for transactional risk prediction
* **pytest**: Testing suite

---

## 3. Installation

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 4. PostgreSQL Setup (Optional)

To connect to PostgreSQL instead of the default SQLite:
1. Ensure your PostgreSQL server is running.
2. Create a database named `supply_chain_finance`.
3. Update `DATABASE_URL` in `.env`:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/supply_chain_finance
   ```

---

## 5. Environment Variables

Create a `.env` file (copied from `.env.example`) in the `backend/` directory:
```env
PROJECT_NAME="AI-Powered Supply-Chain Financing Marketplace"
DEBUG=True
DATABASE_URL=sqlite:///./supply_chain.db
SECRET_KEY=94e7732a392b4fa3e46c7bc3793df6033bb27e025b392cd97dfebf65e2beec9a
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=180
RISK_THRESHOLD_LOW=30
RISK_THRESHOLD_MEDIUM=60
UPLOAD_DIR=uploads
```

---

## 6. How to Run the Backend

Start the ASGI dev server:
```bash
uvicorn app.main:app --reload
```
Once running, the interactive API documentation (Swagger UI) is available at:
* **http://127.0.0.1:8000/docs**

---

## 7. How to Train the Risk Model

The RandomForest risk model is trained automatically on mock/synthetic data during the database seeding process when the application starts for the first time.
To manually trigger model training, execute:
```bash
python -c "from app.ai.risk_model import train_model; train_model()"
```
This will save the trained model binary to `ml_models/risk_model.joblib`.

---

## 8. How to Seed Demo Data

The database is seeded automatically with demo records on application startup if the database is blank. You can log in using the credentials below to demonstrate the marketplace immediately.

### Demo Credentials

| Role | Email | Password | Purpose |
|---|---|---|---|
| **Supplier** | `supplier@example.com` | `password123` | Upload invoices, accept financier offers |
| **Buyer** | `buyer@example.com` | `password123` | Confirm/reject invoices, settle payments |
| **Financier 1** | `financier1@example.com` | `password123` | Alpha Capital (Low risk, large capital, lower rates) |
| **Financier 2** | `financier2@example.com` | `password123` | Beta Finance (Medium risk, fast speed, medium rates) |
| **Financier 3** | `financier3@example.com` | `password123` | Gamma Ventures (High risk, ultra-fast, high rates) |
| **Financier 4** | `financier4@example.com` | `password123` | Delta Debt (Low risk NBFC) |
| **Admin** | `admin@example.com` | `password123` | View all platform records, run calculations |

---

## 9. API Endpoint List

### Authentication
* `POST /auth/register` - Create user
* `POST /auth/login` - Get JWT Access Token
* `GET /auth/me` - Get current user profile

### Suppliers
* `GET /suppliers/dashboard` - Supplier metrics
* `GET /suppliers/invoices` - List uploaded invoices

### Buyers
* `GET /buyers/dashboard` - Buyer metrics
* `GET /buyers/verifications` - Pending invoice confirmations
* `POST /buyers/invoices/{invoice_id}/approve` - Approve verification
* `POST /buyers/invoices/{invoice_id}/reject` - Reject verification

### Invoices
* `POST /invoices/upload` - Upload PDF/Image invoices
* `GET /invoices/{invoice_id}` - Detailed invoice properties
* `GET /invoices` - List invoices according to user context

### Verification
* `GET /verification/{invoice_id}` - Detailed verification report
* `POST /verification/{invoice_id}/approve` - Buyer confirmation
* `POST /verification/{invoice_id}/reject` - Buyer rejection

### Risk Engine
* `POST /risk/{invoice_id}/calculate` - Trigger risk modeling
* `GET /risk/{invoice_id}` - View risk results

### Matching Engine
* `POST /matching/{invoice_id}` - Trigger matching for verified invoice
* `GET /matching/{invoice_id}` - Fetch matches

### Offers
* `POST /offers` - Financier submits bidding offer
* `GET /offers/invoice/{invoice_id}` - List/Rank offers for supplier review
* `POST /offers/{offer_id}/accept` - Supplier accepts offer (triggers transaction)

### Transactions
* `GET /transactions` - List transactions
* `POST /transactions/{transaction_id}/fund` - Financier funds approved invoice
* `POST /transactions/{transaction_id}/settle` - Buyer pays financier

---

## 10. Example Workflow

1. **Login as Supplier**: Call `POST /auth/login` with `supplier@example.com` and copy the JWT token. Add it to the Authorize header in Swagger (`Bearer <token>`).
2. **Upload Invoice**: Call `POST /invoices/upload` uploading an invoice image/pdf file and select `buyer_id` = 2.
3. **Verify Invoice (Buyer)**: Log in as Buyer (`buyer@example.com`). Call `POST /verification/{invoice_id}/approve`.
4. **Evaluate Risk**: Call `POST /risk/{invoice_id}/calculate` (Supplier/Admin auth) to run the ML model.
5. **Run matching**: Call `POST /matching/{invoice_id}` to compute eligibility and suitabilities of financiers.
6. **Submit Offers (Financiers)**: Log in as `financier1@example.com` and `financier2@example.com` to call `POST /offers` submitting competitive terms.
7. **Accept Offer (Supplier)**: Log in as Supplier, check rankings via `GET /offers/invoice/{invoice_id}` and call `POST /offers/{offer_id}/accept`.
8. **Fund (Financier)**: Log in as Financier and call `POST /transactions/{transaction_id}/fund`.
9. **Settle (Buyer)**: Log in as Buyer and call `POST /transactions/{transaction_id}/settle`.

---

## 11. Known Limitations & Future Scope

* **Mock OCR Fallback**: If PaddleOCR is not installed, the system falls back to text regex extraction. Real productions should run dedicated cloud vision APIs.
* **Database Migrations**: This prototype relies on `Base.metadata.create_all()` on startup. In production, use Alembic for managing DB migrations.
* **Online Learning**: Feedback logs are stored in transaction outcomes but not actively retraining the model in real time. Future enhancements will retrain models periodically.
