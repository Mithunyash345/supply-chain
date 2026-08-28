import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine, Base
from app.api.api import router as api_router

# Create tables in the database if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Supply Chain API",
    description="Backend API for the Supply Chain management application",
    version="1.0.0",
)

# Configure CORS so React frontend can fetch from this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Supply Chain API!",
        "docs_url": "/docs",
        "status": "running"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
