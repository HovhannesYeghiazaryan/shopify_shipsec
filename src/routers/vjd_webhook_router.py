"""Webhook routes for VJD events.

Currently handles the "order paid" webhook to validate a customer's code,
place a fulfillment hold, and create a draft order on ShipSec.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.utils import (
    validate_code,
    get_customer_id_from_address,
    check_existing_draft_order,
    save_order,
    save_shipsec_order,
    add_vjd_order_number_to_metafield,
    get_fulfillment_order_id,
    place_fulfillment_hold,
    create_draft_order_on_shipsec,
)
import logging


webhook_router = APIRouter(prefix="/vjd/webhook")

@webhook_router.api_route("/orders/paid", methods=["POST"])
async def orders_paid_webhook_vjd(request: Request):
    """Process VJD 'orders/paid' webhook.

    Steps:
    1) Parse payload and extract address2 as validation code
    2) Validate code and map to customer/variant
    3) Prevent duplicates, fetch fulfillment order, place hold
    4) Create draft order on ShipSec, persist, and add metafield
    """
    try:
        # Parse webhook JSON payload.
        data = await request.json()
        order_id = data.get("id")
        vjd_order_number = data.get("order_number")
        shipping_address = data.get("shipping_address", {})
        # Normalize address2 (code) to avoid whitespace/None issues
        address2 = (shipping_address.get("address2") or "").strip()
        created_at = data.get("created_at")

        def fail(message):
            logging.error(f"400: {message}")
            return JSONResponse({"status": "failure", "message": message}, status_code=400)

        # Required validation code
        if not address2:
            return fail("Address2 (validation code) is required in shipping_address")

        # Check code validity in DB
        is_valid, _, _ = await validate_code(address2)
        if not is_valid:
            return fail(f"Invalid validation code: {address2}")

        # Resolve to customer_id and product variant_id
        customer_id, variant_id = await get_customer_id_from_address(address2)
        if not (customer_id and variant_id):
            return fail(f"Customer not found for validation code: {address2}")

        # Ensure we don't create duplicate draft orders for same VJD order
        if await check_existing_draft_order(order_id):
            return fail(f"Draft order already exists for this VJD order ID: {order_id}")

        # Fetch fulfillment order from VJD by Shopify order ID
        fulfillment_order_id = await get_fulfillment_order_id(order_id)

        if not fulfillment_order_id:
            return fail("Fulfillment order ID not found")

        # Place a hold while draft order is created
        if not await place_fulfillment_hold(fulfillment_order_id):
            return fail("Failed to place order on hold")

        # Create a draft order in ShipSec for the mapped variant
        draft_order = await create_draft_order_on_shipsec(customer_id, variant_id)
        if not draft_order:
            return fail("Failed to create draft order")

        shipsec_order_number = draft_order.get("draft_order", {}).get("id")
        shipsec_number = draft_order.get("draft_order", {}).get("id")
        # Persist both the VJD and ShipSec sides and link via metafield
        await save_order(order_id, address2, vjd_order_number, shipsec_number)
        await save_shipsec_order(order_id, shipsec_order_number, vjd_order_number, created_at, shipsec_number)
        await add_vjd_order_number_to_metafield(shipsec_order_number, vjd_order_number)

        return JSONResponse({
            "status": "success",
            "message": "Order processed, placed on hold, and draft order created on ShipSec successfully"
        }, status_code=200)
    except Exception as e:
        logging.error(f"500: {str(e)}")
        return JSONResponse({"status": "failure", "message": str(e)}, status_code=500)

vjd_webhook_router = webhook_router 