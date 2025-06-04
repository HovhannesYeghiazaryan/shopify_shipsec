from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from src.database.database import DatabaseManager
from src.models.base_model import CustomerCreate, CustomerUpdate, OrderCreate
from src.models.customer import Customer as CustomerORM
from src.utils import save_shipsec_order, check_existing_draft_order
import logging

router = APIRouter(prefix="/customers")
db_manager = DatabaseManager()

@router.post("/", response_model=dict)
async def create_customer(customer: CustomerCreate):
    try:
        new_customer = await db_manager.save_customer(
            customer.customer_name, customer.simple_code, customer.signature_code
        )
        return {"id": new_customer.id, "customer_name": new_customer.customer_name}
    except SQLAlchemyError as db_exc:
        logging.error(f"Database error: {db_exc}")
        return JSONResponse(content={"error": "Database error"}, status_code=500)
    except Exception as e:
        logging.error(f"Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.get("/{customer_id}", response_model=dict)
async def get_customer(customer_id: int = Path(..., description="The ID of the customer to retrieve")):
    try:
        async with db_manager.AsyncSessionLocal() as session:
            customer = await session.get(CustomerORM, customer_id)
            if not customer:
                return JSONResponse(content={"error": "Customer not found"}, status_code=404)
            return {
                "id": customer.id,
                "customer_name": customer.customer_name,
                "simple_code": customer.simple_code,
                "signature_code": customer.signature_code
            }
    except SQLAlchemyError as db_exc:
        logging.error(f"Database error: {db_exc}")
        return JSONResponse(content={"error": "Database error"}, status_code=500)
    except Exception as e:
        logging.error(f"Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.put("/{customer_id}", response_model=dict)
async def update_customer(customer_id: int, customer: CustomerUpdate):
    try:
        async with db_manager.AsyncSessionLocal() as session:
            db_customer = await session.get(CustomerORM, customer_id)
            if not db_customer:
                return JSONResponse(content={"error": "Customer not found"}, status_code=404)
            for field, value in customer.dict(exclude_unset=True).items():
                setattr(db_customer, field, value)
            await session.commit()
            await session.refresh(db_customer)
            return {
                "id": db_customer.id,
                "customer_name": db_customer.customer_name,
                "simple_code": db_customer.simple_code,
                "signature_code": db_customer.signature_code
            }
    except SQLAlchemyError as db_exc:
        logging.error(f"Database error: {db_exc}")
        return JSONResponse(content={"error": "Database error"}, status_code=500)
    except Exception as e:
        logging.error(f"Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.delete("/{customer_id}", response_model=dict)
async def delete_customer(customer_id: int):
    try:
        async with db_manager.AsyncSessionLocal() as session:
            db_customer = await session.get(CustomerORM, customer_id)
            if not db_customer:
                return JSONResponse(content={"error": "Customer not found"}, status_code=404)
            await session.delete(db_customer)
            await session.commit()
            return {"status": "deleted"}
    except SQLAlchemyError as db_exc:
        logging.error(f"Database error: {db_exc}")
        return JSONResponse(content={"error": "Database error"}, status_code=500)
    except Exception as e:
        logging.error(f"Error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/{customer_id}/orders/", response_model=dict)
async def create_order_for_customer(customer_id: int, order: OrderCreate):
    """
    Create a new order for a customer and save it to the orders table.
    """
    try:
        # Optionally, validate the customer exists
        async with db_manager.AsyncSessionLocal() as session:
            customer = await session.get(CustomerORM, customer_id)
            if not customer:
                return JSONResponse(content={"error": "Customer not found"}, status_code=404)

        # Save the order (use your utility, or direct SQLAlchemy if you prefer)
        new_order = await save_shipsec_order(
            order_id=order.shopify_order_id,
            shipsec_order_number=order.validation_code,
            vjd_order_id=order.vjd_order_number,
            created_at=order.created_at,
            shipsec_number=order.shipsec_number
        )
        if new_order:
            return {"status": "success", "order_id": new_order.id}
        else:
            return JSONResponse(content={"error": "Failed to save order"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

customers_router = router 