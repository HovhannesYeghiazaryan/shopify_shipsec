import json
import logging
from random import choices
from string import ascii_lowercase, digits
import hmac
import hashlib
from base64 import b64encode
import httpx
import certifi
import os
from datetime import datetime, timezone
import aiohttp
import ssl

from get_env_values import SHIPSEC_BASE_URL, SHOPIFY_API_VERSION, SHIPSEC_API_KEY, VJD_BASE_URL, VJD_API_KEY
from src.database.database import DatabaseManager
from src.models.customer import Customer, Order, Base

db_manager = DatabaseManager()

def to_naive_utc(dt):
    if dt is None:
        return datetime.utcnow()
    if dt.tzinfo is not None:
        # Convert to UTC, then remove tzinfo
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def generate_code(prefix):
    """
    Generate a unique code for the customer with the given prefix.
    Returns a string like 'prefixxxxxxxxxxxxx'.
    """
    random_string = ''.join(choices(ascii_lowercase + digits, k=12))
    return f"{prefix}{random_string}"

def verify_shopify_webhook(data, hmac_header, secret):
    """
    Verify Shopify webhook signature using HMAC-SHA256.
    Returns True if the signature is valid, False otherwise.
    """
    calculated_hmac = b64encode(
        hmac.new(secret.encode('utf-8'), data, hashlib.sha256).digest()
    ).decode('utf-8')
    return hmac.compare_digest(calculated_hmac, hmac_header)

async def add_metafields_to_customer(customer_id, simple_code, signature_code):
    """
    Add metafields to a Shopify customer using the Shopify API.
    Sends two metafields: simple_forwarding_code and signature_forwarding_code.
    Raises an exception if the API call fails.
    """
    url = f"{SHIPSEC_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/customers/{customer_id}/metafields.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHIPSEC_API_KEY
    }
    metafields = [
        {
            "namespace": "shipsec",
            "key": "simple_code",
            "value": simple_code,
            "type": "single_line_text_field"
        },
        {
            "namespace": "shipsec",
            "key": "signature_code",
            "value": signature_code,
            "type": "single_line_text_field"
        }
    ]
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(headers=headers) as client:
        for metafield in metafields:
            payload = {"metafield": metafield}
            async with client.post(url, data=json.dumps(payload), ssl=ssl_context) as response:
                text = await response.text()
                if response.status != 201:
                    raise Exception(f"Failed to add metafield: {text}")

async def add_metafields_to_customer_notify_response(customer_id, simple_code, signature_code):
    """
    Add metafields to Shopify customer (using 'simple_code' and 'signature_code' as keys) and return the responses.
    Returns a list of response JSONs for notification or further processing.
    Raises an exception if any API call fails.
    """
    url = f"{SHIPSEC_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/customers/{customer_id}/metafields.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHIPSEC_API_KEY
    }
    metafields = [
        {
            "namespace": "shipsec",
            "key": "simple_code",
            "value": simple_code,
            "type": "single_line_text_field"
        },
        {
            "namespace": "shipsec",
            "key": "signature_code",
            "value": signature_code,
            "type": "single_line_text_field"
        }
    ]
    responses = []
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession(headers=headers) as client:
        for metafield in metafields:
            payload = {"metafield": metafield}
            async with client.post(url, data=json.dumps(payload), ssl=ssl_context) as response:
                text = await response.text()
                if response.status != 201:
                    raise Exception(f"Failed to add metafield: {text}")
                resp_json = await response.json()
                responses.append(resp_json)
    return responses

async def notify_shopify_app(shopify_app_url, customer_name, simple_code, signature_code):
    """
    Notify the Shopify app backend (your own backend, not Shopify API) with the generated codes and customer name.
    Sends a POST request to the given shopify_app_url with the data as JSON.
    Returns the response JSON or raises an exception on failure.
    """
    payload = {
        "customer_name": customer_name,
        "simple_code": simple_code,
        "signature_code": signature_code
    }
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    async with aiohttp.ClientSession() as client:
        async with client.post(shopify_app_url, json=payload, ssl=ssl_context) as response:
            response.raise_for_status()
            return await response.json()

async def validate_code(code: str):
    """
    Validate if the given code (simple_code or signature_code) exists in the customers table.
    Returns (is_valid, match_type, customer_id):
      - is_valid: True if valid, False otherwise
      - match_type: 'simple_code', 'signature_code', or None
      - customer_id: the matched customer id or None
    """
    try:
        async with db_manager.AsyncSessionLocal() as session:
            result = await session.execute(
                Customer.__table__.select().where(
                    (Customer.simple_code == code) | (Customer.signature_code == code)
                )
            )
            row = result.first()
        if row:
            customer = row[0] if isinstance(row, tuple) else row
            if customer.simple_code == code:
                match_type = 'simple_code'
            elif customer.signature_code == code:
                match_type = 'signature_code'
            else:
                match_type = None
            return True, match_type, customer.shopify_customer_id
        else:
            return False, None, None
    except Exception as e:
        return False, None, None

# --- Customer Save ---
async def save_customer(shopify_customer_id, customer_name, simple_code, signature_code, email, address1, address2, city, province, country, zip):
    return await db_manager.save_customer(
        shopify_customer_id, customer_name, simple_code, signature_code, email, address1, address2, city, province, country, zip
    )

# --- Order Save ---
async def save_order(shopify_order_id, validation_code, vjd_order_number=None, shipsec_number=None):
    existing_order = await get_order_by_shopify_id(shopify_order_id)
    if existing_order:
        return None  # or False, or a custom error object
    return await db_manager.save_order(
        str(shopify_order_id),
        str(validation_code),
        str(vjd_order_number) if vjd_order_number is not None else None,
        None,  # created_at is not passed here, keep as None or add if needed
        str(shipsec_number) if shipsec_number is not None else None
    )

# --- Order Query ---
async def get_order_by_shopify_id(shopify_order_id):
    return await db_manager.get_order_by_shopify_id(str(shopify_order_id))

async def check_existing_order(vjd_order_number):
    return await db_manager.check_existing_order(vjd_order_number)

# --- Get Secret for Store ---
def get_secret_for_store(store_domain):
    if store_domain == 'shipsec.myshopify.com':
        return os.getenv("SHIPSEC_WEBHOOK_SECRET")
    elif store_domain == 'glocal-vision.myshopify.com':
        return os.getenv("VJD_WEBHOOK_SECRET")
    else:
        return None

# --- Fulfillment Order ID from Shopify ---
async def get_fulfillment_order_id(order_id):
    try:
        url = f"{VJD_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/orders/{order_id}/fulfillment_orders.json"
        headers = {
            "X-Shopify-Access-Token": VJD_API_KEY,
            "Content-Type": "application/json"
        }

        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, ssl=ssl_context) as response:
                text = await response.text()
                logging.info(f"Shopify fulfillment_orders response: {text}")
                response.raise_for_status()  # Raises for non-2xx
                data = await response.json()
                fulfillment_orders = data.get("fulfillment_orders", [])

                if not fulfillment_orders:
                    logging.warning(f"No fulfillment orders found for order ID: {order_id}")
                    return None

                fulfillment_order_id = fulfillment_orders[0].get("id")
                if not fulfillment_order_id:
                    logging.error(f"Fulfillment order ID missing in response for order ID: {order_id}")
                    return None

                logging.info(f"Successfully retrieved fulfillment order ID: {fulfillment_order_id} for order ID: {order_id}")
                return fulfillment_order_id

    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP error occurred while fetching fulfillment order ID: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error while fetching fulfillment order ID: {str(e)}")
        return None

async def get_customer_id_from_address(address2: str):
    """
    Retrieve the customer ID and variant ID from the database using address2 as the lookup key.
    Variant ID is determined by which code matches.
    """
    try:
        logging.info(f"Looking up customer with address2: {address2}")
        async with db_manager.AsyncSessionLocal() as session:
            result = await session.execute(
                Customer.__table__.select().where(
                    (Customer.simple_code == address2) | (Customer.signature_code == address2)
                )
            )
            row = result.first()
        if row:
            customer = row[0] if isinstance(row, tuple) else row
            customer_id = customer.shopify_customer_id
            if customer.simple_code == address2:
                variant_id = 45912383422713  # Variant ID for 'shipsec'
            elif customer.signature_code == address2:
                variant_id = 45912390435065  # Variant ID for 'shipsecsig'
            else:
                logging.error(f"Invalid validation code: {address2}")
                return None, None
            logging.info(f"Customer found: {customer_id}, Variant ID: {variant_id}")
            return customer_id, variant_id
        else:
            logging.error(f"No customer found for address2 code: {address2}")
            return None, None
    except Exception as e:
        logging.error(f"Error retrieving customer ID from database: {str(e)}")
        return None, None

async def check_existing_draft_order(vjd_order_id: str) -> bool:
    """
    Check if the VJD order ID already exists in the orders table (vjd_order_number column).
    Returns True if a draft order already exists for this VJD order ID, otherwise False.
    Logs the result for debugging and traceability.
    """
    try:
        # Ensure vjd_order_id is always a string for the query
        vjd_order_id_str = str(vjd_order_id)
        async with db_manager.AsyncSessionLocal() as session:
            # Query for an order with the given VJD order number
            result = await session.execute(
                Order.__table__.select().where(Order.vjd_order_number == vjd_order_id_str)
            )
            order = result.first()
        if order:
            logging.info(f"Draft order already exists for VJD order ID {vjd_order_id}. Skipping draft order creation.")
            return True
        else:
            logging.info(f"No draft order found for VJD order ID {vjd_order_id}. Proceeding with creation.")
            return False
    except Exception as e:
        logging.error(f"Error checking existing draft order for VJD order ID {vjd_order_id}: {str(e)}")
        return False

async def place_fulfillment_hold(fulfillment_order_id: str) -> bool:
    """
    Place the fulfillment order on hold using Shopify's GraphQL API.
    This function sends a GraphQL mutation to Shopify to place a hold on the given fulfillment order.
    Returns True if the hold is placed successfully, otherwise False.
    Logs all important steps and errors for traceability.
    """
    try:
        # Shopify API URL for GraphQL endpoint
        url = f"{VJD_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

        # Ensure fulfillment_order_id is in the correct Shopify GID format
        fulfillment_order_gid = f"gid://shopify/FulfillmentOrder/{fulfillment_order_id}"

        # The GraphQL mutation for holding the fulfillment order
        query = """
        mutation FulfillmentOrderHold($fulfillmentHold: FulfillmentOrderHoldInput!, $id: ID!) {
          fulfillmentOrderHold(fulfillmentHold: $fulfillmentHold, id: $id) {
            fulfillmentOrder { id }
            remainingFulfillmentOrder { id }
            userErrors { field message }
          }
        }
        """

        # Variables for the mutation
        variables = {
            "fulfillmentHold": {
                "notifyMerchant": True,
                "reason": "OTHER",  # Using a valid reason for the hold
                "reasonNotes": "Used validation code"
            },
            "id": fulfillment_order_gid
        }

        headers = {
            'X-Shopify-Access-Token': VJD_API_KEY,
            'Content-Type': 'application/json'
        }

        # Send the GraphQL request to Shopify asynchronously
        async with aiohttp.ClientSession() as client:
            async with client.post(url, json={'query': query, 'variables': variables}, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'errors' in data:
                        logging.error(f"Error placing hold on fulfillment order {fulfillment_order_id}: {data['errors']}")
                        return False
                    else:
                        logging.info(f"Fulfillment hold placed successfully for fulfillment order {fulfillment_order_id}.")
                        return True
                else:
                    text = await response.text()
                    logging.error(f"Error placing hold on fulfillment order {fulfillment_order_id}: {response.status}, {text}")
                    return False
    except Exception as e:
        logging.error(f"Error placing fulfillment hold on fulfillment order {fulfillment_order_id}: {str(e)}")
        return False

async def create_draft_order_on_shipsec(customer_id: str, variant_id: int):
    """
    Create a draft order on ShipSec using the customer ID and the provided variant ID.
    This function fetches the customer data (including default address and email),
    then creates a draft order with the specified variant. Returns the response JSON
    if successful, otherwise False. Logs all important steps and errors.
    """
    try:
        logging.debug(f"Starting draft order creation for customer {customer_id} with variant {variant_id}.")

        # Retrieve customer data using the customer_id to get their default shipping address and email
        customer_url = f"{SHIPSEC_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/customers/{customer_id}.json"
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(headers={'X-Shopify-Access-Token': SHIPSEC_API_KEY}) as client:
            async with client.get(customer_url, ssl=ssl_context) as customer_response:
                if customer_response.status != 200:
                    text = await customer_response.text()
                    logging.error(f"Error fetching customer data: {customer_response.status}, {text}")
                    return False
                customer_data = await customer_response.json()
                customer = customer_data.get("customer")
                if not customer:
                    logging.error(f"Customer data not found for ID {customer_id}")
                    return False

                # Get the customer's default address
                default_address = customer.get("default_address")
                if not default_address:
                    logging.error(f"No default address found for customer {customer_id}")
                    return False

                # Extract customer details for draft order
                customer_email = customer.get("email", "")
                first_name = default_address.get("first_name", "")
                last_name = default_address.get("last_name", "")

                # Prepare the data for the draft order
                order_data = {
                    "draft_order": {
                        "customer_id": customer_id,
                        "email": customer_email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "line_items": [
                            {
                                "variant_id": variant_id,
                                "quantity": 1
                            }
                        ],
                        "status": "open",
                        "shipping_address": {
                            "address1": default_address.get("address1", ""),
                            "address2": (default_address.get("address2") or '').strip(),
                            "city": default_address.get("city", ""),
                            "province": default_address.get("province", ""),
                            "country": default_address.get("country", ""),
                            "zip": default_address.get("zip", ""),
                        }
                    }
                }

                # ShipSec API URL to create the draft order
                shipsec_url = f"{SHIPSEC_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/draft_orders.json"

                # Send the request to ShipSec API
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                async with aiohttp.ClientSession(headers={'X-Shopify-Access-Token': SHIPSEC_API_KEY}) as client:
                    async with client.post(shipsec_url, json=order_data, ssl=ssl_context) as response:
                        if response.status in [201, 202]:
                            logging.info(f"Draft order created successfully for customer {customer_id}.")
                            return await response.json()
                        else:
                            text = await response.text()
                            logging.error(f"Failed to create draft order: {response.status} {text}")
                            return False
    except Exception as e:
        logging.error(f"Error creating draft order on ShipSec: {e}")
        return False

async def add_vjd_order_number_to_metafield(shipsec_order_number: str, vjd_order_number: str):
    """
    Add the VJD order number as a metafield to the ShipSec draft order.
    This function sends a POST request to the ShipSec API to add a custom metafield
    (namespace: 'custom', key: 'vjd_order_number') to the specified draft order.
    Logs all important steps and errors for traceability.
    """
    try:
        # Construct the URL to update metafields on ShipSec
        url = f"{SHIPSEC_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/draft_orders/{shipsec_order_number}/metafields.json"

        # Set headers with Content-Type and API key for ShipSec
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": SHIPSEC_API_KEY
        }

        # Define the metafield payload to be added
        metafield = {
            "namespace": "custom",
            "key": "vjd_order_number",
            "value": vjd_order_number,
            "type": "single_line_text_field"
        }
        payload = {"metafield": metafield}

        # Make the POST request to ShipSec's API to add the metafield
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        async with aiohttp.ClientSession(headers=headers) as client:
            async with client.post(url, headers=headers, json=payload, ssl=ssl_context) as response:
                if response.status == 201:
                    logging.info(f"Metafield added successfully: {await response.json()}")
                else:
                    text = await response.text()
                    raise Exception(f"Failed to add metafield: {text}")

    except Exception as e:
        logging.error(f"Error adding VJD order number to ShipSec metafield: {str(e)}")

async def save_shipsec_order(order_id: str, shipsec_order_number: str, vjd_order_id: str, created_at, shipsec_number: str):
    """
    Save ShipSec order data to the database, including the ShipSec order number.
    This function inserts a new order into the orders table with all relevant fields.
    Logs all important steps and errors for traceability.
    Returns the new Order instance if successful, otherwise None.
    """
    try:
        # Check for existing order
        existing_order = await db_manager.get_order_by_shopify_id(str(order_id))
        if existing_order:
            logging.error(f"Order with Shopify order ID {order_id} already exists.")
            return None

        async with db_manager.AsyncSessionLocal() as session:
            # Convert created_at to datetime if it's a string
            if isinstance(created_at, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at)
                except Exception:
                    created_at_dt = datetime.utcnow()
            elif isinstance(created_at, datetime):
                created_at_dt = created_at
            else:
                created_at_dt = datetime.utcnow()

            created_at_dt = to_naive_utc(created_at_dt)

            new_order = Order(
                shopify_order_id=str(order_id),
                validation_code=str(shipsec_order_number),
                vjd_order_number=str(vjd_order_id) if vjd_order_id is not None else None,
                created_at=created_at_dt,
                shipsec_number=str(shipsec_number) if shipsec_number is not None else None
            )
            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)
            logging.info(f"ShipSec order {order_id} with ShipSec order number {shipsec_order_number} saved successfully.")
            return new_order
    except Exception as e:
        logging.error(f"Error saving ShipSec order: {str(e)}")
        return None

async def get_order_metafields_from_shipsec(shipsec_order_id):
    """Fetch the order metafields from ShipSec API for a given ShipSec order ID."""
    try:
        url = f"{SHIPSEC_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/orders/{shipsec_order_id}/metafields.json"
        headers = {
            "X-Shopify-Access-Token": SHIPSEC_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        ssl_context = ssl.create_default_context()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    logging.error(f"Failed to retrieve metafields for order {shipsec_order_id}: {text}")
                    return None
    except Exception as e:
        logging.error(f"Error fetching metafields from ShipSec: {str(e)}")
        return None

def parse_draft_order_id_from_metafields(metafields_json):
    """Parse the draft_order_id from the ShipSec metafields JSON."""
    try:
        # Look for the custom metafield that contains the draft order ID
        metafield = next((item for item in metafields_json.get("metafields", []) if item.get("namespace") == "custom" and item.get("key") == "draft_id"), None)
        if metafield:
            # Extract the draft order ID from the "value" field
            draft_order_gid = metafield.get("value", "")
            # Remove the "Insert Variable " prefix if it exists
            if draft_order_gid.startswith("Insert Variable "):
                draft_order_gid = draft_order_gid.replace("Insert Variable ", "")
            # Ensure the value starts with "gid://shopify/DraftOrder/"
            if draft_order_gid.startswith("gid://shopify/DraftOrder/"):
                # Extract the numeric part after the prefix "gid://shopify/DraftOrder/"
                draft_order_id = draft_order_gid.split("/")[-1]  # Get the last part of the string
                return draft_order_id
            else:
                logging.error(f"Unexpected draft order ID format: {draft_order_gid}")
                return None
        else:
            logging.error("Draft order ID not found in metafields.")
            return None
    except Exception as e:
        logging.error(f"Error parsing draft order ID: {str(e)}")
        return None

async def get_vjd_order_id_from_shipsec_order(draft_order_id):
    """Fetch the VJD order ID from the orders table using the ShipSec order (draft) ID."""
    try:
        async with db_manager.AsyncSessionLocal() as session:
            from src.models.customer import Order
            result = await session.execute(
                Order.__table__.select().where(Order.shipsec_number == str(draft_order_id))
            )
            row = result.first()
        if row:
            order = row[0] if isinstance(row, tuple) else row
            shopify_order_id = order.shopify_order_id
            logging.info(f"Found VJD order number {shopify_order_id} for ShipSec draft order ID {draft_order_id}")
            return shopify_order_id
        else:
            logging.warning(f"No VJD order found for ShipSec draft order ID {draft_order_id}")
            return None
    except Exception as e:
        logging.error(f"Error fetching VJD order ID for ShipSec order {draft_order_id}: {str(e)}")
        return None

async def get_fulfillment_order_id_from_vjd(vjd_order_id):
    """Fetch the fulfillment order ID from VJD using the VJD order ID."""
    try:
        url = f"{VJD_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/orders/{vjd_order_id}/fulfillment_orders.json"
        logging.warning(f"Shopify fulfillment_orders URL for VJD order {vjd_order_id}: {url}")
        headers = {"X-Shopify-Access-Token": VJD_API_KEY}
        ssl_context = ssl.create_default_context()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    data = await response.json()
                    logging.warning(f"Shopify fulfillment_orders response for VJD order {vjd_order_id}")
                    fulfillment_orders = data.get("fulfillment_orders", [])
                    if fulfillment_orders:
                        return fulfillment_orders[0].get("id")
                    else:
                        return None
                else:
                    text = await response.text()
                    logging.error(f"Error fetching fulfillment order ID for VJD order {vjd_order_id}: {response.status} {text}")
                    return None
    except Exception as e:
        logging.error(f"Error fetching fulfillment order ID for VJD order {vjd_order_id}: {str(e)}")
        return None

async def release_hold_on_vjd_order(fulfillment_order_id):
    """Release the hold on the VJD order using Shopify's GraphQL API."""
    try:
        url = f"{VJD_BASE_URL}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        query = """
        mutation FulfillmentOrderReleaseHold($id: ID!) {
          fulfillmentOrderReleaseHold(id: $id) {
            fulfillmentOrder {
              id
              status
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {"id": f"gid://shopify/FulfillmentOrder/{fulfillment_order_id}"}
        headers = {"X-Shopify-Access-Token": VJD_API_KEY, "Content-Type": "application/json"}
        ssl_context = ssl.create_default_context()
        logging.info(f"Releasing hold: url={url}, fulfillment_order_id={fulfillment_order_id}, headers={headers}")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"query": query, "variables": variables}, headers=headers, ssl=ssl_context) as response:
                body = await response.text()
                logging.info(f"Shopify response: status={response.status}, body={body}")
                if response.status == 200:
                    data = json.loads(body)
                    if "errors" in data:
                        logging.error(f"Error releasing hold: {data['errors']}")
                        return False
                    return True
                else:
                    logging.error(f"Error releasing hold on fulfillment order {fulfillment_order_id}: {response.status}")
                    return False
    except Exception as e:
        logging.error(f"Error releasing hold on fulfillment order {fulfillment_order_id}: {str(e)}")
        return False