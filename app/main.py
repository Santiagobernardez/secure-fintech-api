from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up — environment: development")
    # We removed the auto-table creation here. Alembic will handle migrations securely.
    yield
    # Shutdown logic
    logger.info("Shutting down API...")

# Initialize FastAPI application
app = FastAPI(
    title="Secure Fintech API",
    description="API for financial operations with DevSecOps standards",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def health_check():
    return {"status": "healthy", "message": "API is running and secure."}