from pydantic import BaseModel, Field
from typing import Optional


class Customer(BaseModel):
    """
    Represents a customer in the database.
    """
    id: int
    customer_name: str
    simple_code: str
    signature_code: str
    email: str
    address1: str
    address2: Optional[str] = None
    city: str
    province: str
    country: str
    zip: str

class CustomerCreate(BaseModel):
    """
    Fields required to create a new customer.
    """
    customer_name: str = Field(max_length=255)
    simple_code: str
    signature_code: str
    email: str
    address1: str
    address2: Optional[str] = None
    city: str
    province: str
    country: str
    zip: str

class CustomerUpdate(BaseModel):
    """
    Fields for updating an existing customer.
    All fields are optional for partial updates.
    """
    customer_name: Optional[str] = Field(default=None, max_length=255)
    simple_code: Optional[str] = None
    signature_code: Optional[str] = None
    email: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None

class Order(BaseModel):
    id: int
    shopify_order_id: str
    validation_code: str
    created_at: str
    vjd_order_number: Optional[str] = None

class OrderCreate(BaseModel):
    shopify_order_id: str
    validation_code: str
    vjd_order_number: Optional[str] = None

class OrderUpdate(BaseModel):
    validation_code: Optional[str] = None
    vjd_order_number: Optional[str] = None