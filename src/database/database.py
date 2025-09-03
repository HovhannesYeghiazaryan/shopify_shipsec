import os
import logging
from operator import itemgetter
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.models.customer import Base, Customer, Order


load_dotenv(os.path.join(os.path.abspath(Path(__file__).parent), "db.env"))


class DatabaseManager:
    """
    Manages the asynchronous database engine, session, and customer data operations.
    Provides methods to initialize the database, get a session, and save a customer.
    """
    def __init__(self):
        """
        Initialize the database connection parameters and create the async engine and sessionmaker.
        """
        self.USER, self.PASSWD, self.DB_NAME, self.HOST, self.PORT = itemgetter(
            "DB_USER", "PASSWD", "DB_NAME", "HOST", "PORT"
        )(os.environ)
        self.DATABASE_URL = f"postgresql+asyncpg://{self.USER}:{self.PASSWD}@{self.HOST}:{self.PORT}/{self.DB_NAME}"
        self.engine = create_async_engine(self.DATABASE_URL, echo=False)  # echo=True for debugging
        self.AsyncSessionLocal = sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """
        Create all tables in the database if they do not exist.
        Should be called at application startup.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Database tables created or verified.")

    async def get_session(self):
        """
        Provide an async database session (as a context manager or dependency).
        Usage: async with db_manager.get_session() as session:
        """
        async with self.AsyncSessionLocal() as session:
            yield session

    async def save_customer(
            self, 
            shopify_customer_id: str, 
            customer_name: str, 
            simple_code: str, 
            signature_code: str, 
            email: str, 
            address1: str, 
            address2: str = None, 
            city: str = '', 
            province: str = '', 
            country: str = '', 
            zip: str = ''):
        """
        Save a new customer record to the database with the given Shopify customer id, name, codes, and address/email fields.
        Commits the transaction and returns the new customer instance.
        """
        async with self.AsyncSessionLocal() as session:
            new_customer = Customer(
                shopify_customer_id=shopify_customer_id,
                customer_name=customer_name,
                simple_code=simple_code,
                signature_code=signature_code,
                email=email,
                address1=address1,
                address2=address2,
                city=city,
                province=province,
                country=country,
                zip=zip
            )
            session.add(new_customer)
            await session.commit()
            await session.refresh(new_customer)
            logging.info(f"Customer data saved: ID={new_customer.id}, Shopify ID={shopify_customer_id}, Name={customer_name}, Email={email}, Address1={address1}, Address2={address2}, City={city}, Province={province}, Country={country}, Zip={zip}, Simple Code={simple_code}, Signature Code={signature_code}")
            return new_customer

    async def save_order(self, shopify_order_id: str, validation_code: str, vjd_order_number: str = None, created_at: datetime = None, shipsec_number: str = None):
        """
        Save a new order record to the database, including shipsec_number.
        Commits the transaction and returns the new order instance.
        """
        async with self.AsyncSessionLocal() as session:
            new_order = Order(
                shopify_order_id=str(shopify_order_id),
                validation_code=str(validation_code),
                vjd_order_number=str(vjd_order_number) if vjd_order_number is not None else None,
                created_at=created_at,
                shipsec_number=str(shipsec_number) if shipsec_number is not None else None
            )
            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)
            logging.info(f"Order data saved: ID={new_order.id}, Shopify Order ID={shopify_order_id}, Validation Code={validation_code}, VJD Order Number={vjd_order_number}, Created At={created_at}, ShipSec Number={shipsec_number}")
            return new_order

    async def get_order_by_shopify_id(self, shopify_order_id: str):
        """
        Retrieve an order by its Shopify order ID.
        Returns the order instance or None if not found.
        """
        async with self.AsyncSessionLocal() as session:
            logging.info(f"Querying for shopify_order_id: '{shopify_order_id}' (len={len(str(shopify_order_id))})")
            result = await session.execute(
                Order.__table__.select().where(Order.shopify_order_id == str(shopify_order_id))
            )
            order = result.first()
            if order:
                logging.info(f"Order found: {order}")
                return order[0] if isinstance(order, tuple) else order
            else:
                logging.error(f"No order found for shopify_order_id: '{shopify_order_id}'")
                # Optionally, print all IDs for debugging
                all_ids = await session.execute(Order.__table__.select())
                all_orders = all_ids.fetchall()
                logging.info(f"All shopify_order_ids in DB: {[row[0] for row in all_orders]}")
                return None

    async def check_existing_order(self, vjd_order_number: str) -> bool:
        """
        Check if an order with the given VJD order number exists.
        Returns True if exists, False otherwise.
        """
        async with self.AsyncSessionLocal() as session:
            result = await session.execute(
                Order.__table__.select().where(Order.vjd_order_number == vjd_order_number)
            )
            order = result.first()
            return bool(order)