import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.database import engine, Base, SessionLocal
from app.database.seed import seed_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Run seed script
    db = SessionLocal()
    try:
        seed_db(db)
        logger.info("Database initialized and seeded successfully.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
    finally:
        db.close()
        
    yield
    # Shutdown logic
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-Powered Supply-Chain Financing Marketplace.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.routers import (
    auth,
    suppliers,
    buyers,
    invoices,
    verification,
    financiers,
    risk,
    matching,
    offers,
    transactions,
)

app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(buyers.router)
app.include_router(invoices.router)
app.include_router(verification.router)
app.include_router(financiers.router)
app.include_router(risk.router)
app.include_router(matching.router)
app.include_router(offers.router)
app.include_router(transactions.router)

@app.get("/health", tags=["Health"])
def health_check():
    """
    Service health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "supply-chain-financing-backend"
    }
