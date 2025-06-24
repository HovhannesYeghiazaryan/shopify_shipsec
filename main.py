from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.database import DatabaseManager
from fastapi.middleware.cors import CORSMiddleware
from src.routers.customers import customers_router
from src.routers.shipsec import shipsec_router
from src.routers.vjd_api_router import vjd_api_router
from src.routers.vjd_webhook_router import vjd_webhook_router
from src.settings import configure_app
import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler for startup and shutdown logic.
    Initializes the database tables when the application starts.
    """
    logger.info("Starting FastAPI application...")
    db_manager = DatabaseManager()
    await db_manager.init_db()
    logger.info("Database initialized successfully")
    yield
    logger.info("Shutting down FastAPI application...")

app = FastAPI(
    title="Shopify ShipSec API",
    description="FastAPI application for Shopify integration with ShipSec",
    version="1.0.0",
    lifespan=lifespan
)

db_manager = DatabaseManager()

configure_app(app)

DEVELOPMENT_MODE = True

# In-memory set to track processed webhook IDs and prevent duplicate processing
processed_webhook_ids = set()

# Enhanced CORS settings for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For ngrok testing - restrict in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Register all routers explicitly
app.include_router(customers_router)
app.include_router(shipsec_router)
app.include_router(vjd_api_router)
app.include_router(vjd_webhook_router)

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "service": "shopify-shipsec-api",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Shopify ShipSec API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }