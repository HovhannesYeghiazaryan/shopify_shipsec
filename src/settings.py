from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.customers import customers_router
from src.routers.shipsec import shipsec_router
from src.routers.vjd_api_router import vjd_api_router
from src.routers.vjd_webhook_router import vjd_webhook_router

# Project-wide configuration
ALLOWED_ORIGINS = ["*"]  # Update for production
ALLOWED_METHODS = ["*"]
ALLOWED_HEADERS = ["*"]
ALLOWED_CREDENTIALS = True


def configure_app(app: FastAPI):
    """
    Apply all middleware, routers, and project-wide settings to the FastAPI app.
    """
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=ALLOWED_CREDENTIALS,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
    # Routers
    app.include_router(customers_router)
    app.include_router(shipsec_router)
    app.include_router(vjd_api_router)
    app.include_router(vjd_webhook_router)
    # Add other global settings/configurations here 