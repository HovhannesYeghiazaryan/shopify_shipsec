from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.utils import validate_code
import logging


api_router = APIRouter(prefix="/vjd/api")


@api_router.api_route("/validate_code", methods=["POST", "OPTIONS"])
async def validate_code_endpoint(request: Request):
    if request.method == "OPTIONS":
        return JSONResponse({}, status_code=200)
    try:
        data = await request.json()
        code = data.get("code")
        if not code or not isinstance(code, str) or not code.strip():
            logging.warning("No code provided in payload.")
            return JSONResponse({"status": "error", "message": "Code is required"}, status_code=400)
        code = code.strip()
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
        logging.error(f"Error in validate_code: {str(e)}")
        import traceback; logging.error(traceback.format_exc())
        return JSONResponse({"status": "error", "message": "Internal server error"}, status_code=500)


vjd_api_router = api_router