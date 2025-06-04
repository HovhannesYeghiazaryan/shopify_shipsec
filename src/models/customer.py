from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    shopify_customer_id = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=False)
    simple_code = Column(String, unique=True, nullable=False)
    signature_code = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    address1 = Column(String, nullable=False)
    address2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    province = Column(String, nullable=False)
    country = Column(String, nullable=False)
    zip = Column(String, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    shopify_order_id = Column(String, unique=True, nullable=False)
    validation_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    vjd_order_number = Column(String, nullable=True)
    shipsec_number = Column(String, nullable=True)