from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.customers import customers_router
from src.routers.shipsec import shipsec_router
from src.routers.vjd_api_router import vjd_api_router
from src.routers.vjd_webhook_router import vjd_webhook_router
import os
import logging

logger = logging.getLogger(__name__)

# Project-wide configuration via env
# Comma-separated list (e.g., "http://localhost:3000,https://admin.shopify.com")
CORS_ALLOW_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
# Regex patterns for dynamic tunnels (e.g., "https://.*\\.ngrok-free\\.app|https://.*\\.trycloudflare\\.com")
CORS_ALLOW_ORIGIN_REGEX = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "").strip() or None
CORS_ALLOW_METHODS = [m.strip() for m in os.getenv("CORS_ALLOW_METHODS", "*").split(",") if m.strip()] or ["*"]
CORS_ALLOW_HEADERS = [h.strip() for h in os.getenv("CORS_ALLOW_HEADERS", "*").split(",") if h.strip()] or ["*"]
CORS_EXPOSE_HEADERS = [h.strip() for h in os.getenv("CORS_EXPOSE_HEADERS", "").split(",") if h.strip()]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "600"))

def configure_app(app: FastAPI):
    """
    Apply all middleware, routers, and project-wide settings to the FastAPI app.
    """
    # Validate credentials + wildcard
    if CORS_ALLOW_CREDENTIALS:
        if not CORS_ALLOW_ORIGINS and not CORS_ALLOW_ORIGIN_REGEX:
            logger.warning("CORS: allow_credentials=True requires explicit origins or regex; refusing '*'")
        if CORS_ALLOW_ORIGINS == ["*"]:
            logger.warning("CORS: '*' with credentials is invalid. Remove '*' or set allow_credentials=false.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[] if CORS_ALLOW_ORIGIN_REGEX else (CORS_ALLOW_ORIGINS or []),
        allow_origin_regex=CORS_ALLOW_ORIGIN_REGEX,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=CORS_ALLOW_METHODS,
        allow_headers=CORS_ALLOW_HEADERS,
        expose_headers=CORS_EXPOSE_HEADERS or None,
        max_age=CORS_MAX_AGE,
    )

    logger.info(
        f"CORS configured: origins={CORS_ALLOW_ORIGINS}, regex={CORS_ALLOW_ORIGIN_REGEX}, "
        f"credentials={CORS_ALLOW_CREDENTIALS}, methods={CORS_ALLOW_METHODS}, headers={CORS_ALLOW_HEADERS}, "
        f"expose={CORS_EXPOSE_HEADERS}, max_age={CORS_MAX_AGE}"
    )

    # Routers
    app.include_router(customers_router)
    app.include_router(shipsec_router)
    app.include_router(vjd_api_router)
    app.include_router(vjd_webhook_router)