"""Application entrypoint and configuration for FastAPI.

Sets up lifespan (startup/shutdown), database initialization, and applies
project-wide settings including CORS and routers.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.database import DatabaseManager
from src.routers.customers import customers_router
from src.routers.shipsec import shipsec_router
from src.routers.vjd_api_router import vjd_api_router
from src.routers.vjd_webhook_router import vjd_webhook_router
from src.settings import configure_app
import logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle handler.

    On startup, initialize database tables. Add any shutdown logic as needed.
    """
    db_manager = DatabaseManager()
    await db_manager.init_db()
    yield
    # (Optional) Add shutdown logic here

# Configure root logger to show INFO in CLI
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(lifespan=lifespan)
db_manager = DatabaseManager()

configure_app(app)

DEVELOPMENT_MODE = True

# In-memory set to track processed webhook IDs and prevent duplicate processing
# processed_webhook_ids = set()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Or restrict to your domains
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Register all routers explicitly
# app.include_router(customers_router)
# app.include_router(shipsec_router)
# app.include_router(vjd_api_router)
# app.include_router(vjd_webhook_router)