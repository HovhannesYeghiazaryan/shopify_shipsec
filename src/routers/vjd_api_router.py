"""API routes for validating customer codes.

This module exposes a single endpoint used by the storefront (e.g., VJD checkout)
to validate a user-provided code against records stored in the database.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.utils import validate_code
import logging


api_router = APIRouter(prefix="/vjd/api")

@api_router.api_route("/validate_code", methods=["POST"])  # Let CORS middleware handle OPTIONS
async def validate_code_endpoint(request: Request):
    """Validate a code from the request body against the database.

    Expects a JSON payload like: {"code": "..."}
    Returns 200 on success with details, 404 if invalid, or 400/500 on errors.
    CORS preflight (OPTIONS) is handled globally by CORSMiddleware.
    """
    try:
        # Parse request body as JSON. If parsing fails, it will be caught below.
        data = await request.json()
        # Extract and normalize the code
        code = data.get("code")
        if not code or not isinstance(code, str) or not code.strip():
            logging.warning("No code provided in payload.")
            return JSONResponse({"status": "error", "message": "Code is required"}, status_code=400)
        code = code.strip()
        # Validate against DB (checks both simple_code and signature_code)
        is_valid, match_type, customer_id = await validate_code(code)
        if is_valid:
            return JSONResponse({
                "status": "success",
                "message": "Code is valid",
                "match_type": match_type,
                "customer_id": customer_id
            }, status_code=200)
        else:
            return JSONResponse({"status": "error", "message": "Invalid code"}, status_code=404)
    except Exception as e:
        # Log the exception and return a generic server error
        logging.error(f"Error in validate_code: {str(e)}")
        import traceback; logging.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": "Internal server error"}, status_code=500)


vjd_api_router = api_router