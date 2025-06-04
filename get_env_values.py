# No need to change anything here
import os
from operator import itemgetter
from dotenv import load_dotenv
import hmac, hashlib, base64
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


load_dotenv()


SHIPSEC_API_KEY, SHIPSEC_BASE_URL, VJD_BASE_URL, WEBHOOK_SECRET, SHOPIFY_API_VERSION, VJD_API_KEY = itemgetter(
    "SHIPSEC_API_KEY", "SHIPSEC_BASE_URL", "VJD_BASE_URL", "WEBHOOK_SECRET", "SHOPIFY_API_VERSION", "VJD_API_KEY"
)(os.environ)

secret = b'{WEBHOOK_SECRET}'
data = b'{"id": 1, "first_name": "TestUser"}'
hmac_header = base64.b64encode(hmac.new(secret, data, hashlib.sha256).digest()).decode()
