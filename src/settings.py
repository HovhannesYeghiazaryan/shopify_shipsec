from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.customers import customers_router
from src.routers.shipsec import shipsec_router
from src.routers.vjd_api_router import vjd_api_router
from src.routers.vjd_webhook_router import vjd_webhook_router

# Project-wide configuration
ALLOWED_ORIGINS = [
    "https://vapejuicedepot.com",
    "https://lion-simple-wrongly.ngrok-free.app",
    "https://extensions.shopifycdn.com"
]

# ALLOW_ORIGIN_REGEX = (
#     r"^https://(www\.)?vapejuicedepot\.com$"
#     r"|^https://checkout\.shopify\.com$"
#     r"|^https://admin\.shopify\.com$"
#     r"|^https://[a-z0-9-]+\.myshopify\.com$"
#     r"|^https://[a-z0-9-]+\.shopifypreview\.com$"
#     r"|^https://[-a-z0-9]+\.ngrok(-free)?\.app$"
#     r"|^https://[-a-z0-9]+\.trycloudflare\.com$"
# )

ALLOWED_METHODS = ["*"]
ALLOWED_HEADERS = ["*"]
ALLOWED_CREDENTIALS = True
ALLOWED_EXPOSE_HEADERS = ["*"]
ALLOWED_MAX_AGE = 86400
ALLOWED_ALLOW_PRIVATE_NETWORK = True


def configure_app(app: FastAPI):
    """
    Apply all middleware, routers, and project-wide settings to the FastAPI app.
    """
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        # allow_origin_regex=ALLOW_ORIGIN_REGEX,
        allow_credentials=ALLOWED_CREDENTIALS,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        expose_headers=ALLOWED_EXPOSE_HEADERS,
        max_age=ALLOWED_MAX_AGE,
    )
    # Routers
    app.include_router(customers_router)
    app.include_router(shipsec_router)
    app.include_router(vjd_api_router)
    app.include_router(vjd_webhook_router)
    # Add other global settings/configurations here 