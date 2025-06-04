from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from src.utils import verify_shopify_webhook, generate_code, add_metafields_to_customer_notify_response, notify_shopify_app, get_order_metafields_from_shipsec, parse_draft_order_id_from_metafields, get_vjd_order_id_from_shipsec_order, get_fulfillment_order_id_from_vjd, release_hold_on_vjd_order
from get_env_values import WEBHOOK_SECRET
from src.database.database import DatabaseManager
import logging

router = APIRouter(prefix="/shipsec/webhook")

db_manager = DatabaseManager()

@router.post("/customers/enable")
async def customers_enable(request: Request, x_shopify_hmac_sha256: str = Header(None)):
    try:
        webhook_data = await request.body()
        DEVELOPMENT_MODE = True
        processed_webhook_ids = set()
        if not DEVELOPMENT_MODE:
            if not verify_shopify_webhook(webhook_data, x_shopify_hmac_sha256, WEBHOOK_SECRET):
                logging.error("Invalid webhook signature")
                return JSONResponse(
                    content={'status': 'failure', 'message': 'Invalid signature'},
                    status_code=400
                )
        customer_data = await request.json()
        shopify_customer_id = str(customer_data.get('id'))
        customer_name = customer_data.get('first_name', 'Unknown')
        email = customer_data.get('email', '')
        default_address = customer_data.get('default_address') or {}
        address1 = default_address.get('address1') or ''
        address2 = (default_address.get('address2') or "").strip()
        city = default_address.get('city') or ''
        province = default_address.get('province') or ''
        country = default_address.get('country') or ''
        zip_code = default_address.get('zip') or ''
        if shopify_customer_id in processed_webhook_ids:
            return JSONResponse(
                content={"status": "ignored", "message": "Duplicate event"},
                status_code=200
            )
        processed_webhook_ids.add(shopify_customer_id)
        simple_code = generate_code("shipsec")
        signature_code = generate_code("shipsecsig")
        try:
            await add_metafields_to_customer_notify_response(
                shopify_customer_id, 
                simple_code, 
                signature_code
            )
        except Exception as e:
            logging.error(f"Failed to add metafields: {e}")
        try:
            new_customer = await db_manager.save_customer(
                shopify_customer_id,
                customer_name,
                simple_code,
                signature_code,
                email,
                address1,
                address2,
                city,
                province,
                country,
                zip_code
            )
        except SQLAlchemyError as db_exc:
            logging.error(f"Database error: {db_exc}")
            return JSONResponse(
                content={"status": "failure", "message": "Database error"},
                status_code=500
            )
        try:
            notify_response = await add_metafields_to_customer_notify_response(
                new_customer.shopify_customer_id, new_customer.simple_code, new_customer.signature_code
            )
            logging.info(f"Notified Shopify app: {notify_response}")
        except Exception as e:
            logging.error(f"Failed to notify Shopify app: {e}")
        try:
            notify_app_response = await notify_shopify_app(
                customer_name,
                simple_code,
                signature_code
            )
            logging.info(f"Notified backend app: {notify_app_response}")
        except Exception as e:
            logging.error(f"Failed to notify backend app: {e}")
        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "customer_id": shopify_customer_id,
                    "simple_forwarding_code": simple_code,
                    "signature_forwarding_code": signature_code
                }
            },
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        import traceback; logging.error(traceback.format_exc())
        return JSONResponse(
            content={"status": "failure", "message": str(e)},
            status_code=500
        )

@router.post("/orders/paid")
async def order_paid_webhook_shipsec(request: Request):
    """Handle ShipSec's 'order paid' webhook."""
    try:
        webhook_data = await request.json()
        logging.info(f"Received ShipSec Webhook Data: {webhook_data}")
        shipsec_order_id = webhook_data.get("id")
        if not shipsec_order_id:
            logging.error("ShipSec order ID is missing in the webhook data.")
            return JSONResponse({"status": "failure", "message": "ShipSec order ID missing"}, status_code=400)

        # Step 2: Fetch the draft order ID from ShipSec API (using metafields)
        # Placeholder for async util function
        order_metafields = await get_order_metafields_from_shipsec(shipsec_order_id)
        if not order_metafields:
            logging.error(f"Failed to retrieve order metafields for ShipSec order ID {shipsec_order_id}.")
            return JSONResponse({"status": "failure", "message": f"Order metafields not found for {shipsec_order_id}"}, status_code=400)

        # Extract the draft order ID from the metafield
        draft_order_id = parse_draft_order_id_from_metafields(order_metafields)
        if not draft_order_id:
            logging.error(f"No draft order ID found for ShipSec order ID {shipsec_order_id}.")
            return JSONResponse({"status": "failure", "message": f"Draft order ID not found for {shipsec_order_id}"}, status_code=400)

        # Step 3: Fetch the corresponding VJD order ID from our shipsec_orders table
        # Placeholder for async util function
        shopify_order_id = await get_vjd_order_id_from_shipsec_order(draft_order_id)
        if not shopify_order_id:
            logging.error(f"No VJD order found for ShipSec order ID {draft_order_id}.")
            return JSONResponse({"status": "failure", "message": f"VJD order not found for {draft_order_id}"}, status_code=400)

        # Step 4: Fetch the fulfillment order ID from VJD using the Shopify order ID from the DB
        # Look up the order in the DB using vjd_order_id to get the shopify_order_id
        # order = await db_manager.get_order_by_shopify_id(str(shipsec_order_id))
        # shopify_order_id = order.shopify_order_id if order else None
        # if not shopify_order_id:
        #     logging.error(f"No Shopify order ID found for ShipSec order ID {shipsec_order_id}.")
        #     return JSONResponse({"status": "failure", "message": f"Shopify order ID not found for {shipsec_order_id}"}, status_code=400)

        fulfillment_order_id = await get_fulfillment_order_id_from_vjd(shopify_order_id)
        if not fulfillment_order_id:
            logging.error(f"No fulfillment order found for Shopify order ID {shopify_order_id}.")
            return JSONResponse({"status": "failure", "message": f"Fulfillment order not found for {shopify_order_id}"}, status_code=400)

        # Step 5: Release the hold on the VJD order
        release_hold_response = await release_hold_on_vjd_order(fulfillment_order_id)
        if release_hold_response:
            logging.info(f"Hold released successfully for Shopify order ID {shopify_order_id}.")
            return JSONResponse({"status": "success", "message": "Hold released successfully"}, status_code=200)
        else:
            logging.error(f"Failed to release hold for Shopify order ID {shopify_order_id}.")
            return JSONResponse({"status": "failure", "message": "Failed to release hold"}, status_code=400)

    except Exception as e:
        logging.error(f"Error processing ShipSec webhook for order: {str(e)}")
        return JSONResponse({"status": "failure", "message": str(e)}, status_code=500)

shipsec_router = router 