import time
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import datetime
from app.database import get_db
from app.models import Order, OrderItem, User, Product

router = APIRouter(prefix="/orders", tags=["orders"])

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]

class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: float

class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    total_amount: float
    created_at: datetime.datetime
    items: List[OrderItemResponse] = []

@router.get("", response_model=List[OrderResponse])
def get_orders(
    request: Request,
    user_id: Optional[int] = Query(None, description="Filter orders by User ID"),
    status: Optional[str] = Query(None, description="Filter orders by Status"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query_start = time.perf_counter()
    query = db.query(Order)

    if user_id is not None:
        # Notice: Query without composite index (user_id, created_at)
        # Forces sequential scan + sort on tens of thousands of orders
        query = query.filter(Order.user_id == user_id)

    if status is not None:
        query = query.filter(Order.status == status)

    # Ordering by created_at DESC is the critical performance bottleneck
    # without composite index idx_orders_user_created(user_id, created_at DESC)
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()

    query_duration_ms = round((time.perf_counter() - query_start) * 1000, 2)
    request.state.db_query_ms = query_duration_ms

    return orders

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    query_start = time.perf_counter()
    order = db.query(Order).filter(Order.id == order_id).first()
    query_duration_ms = round((time.perf_counter() - query_start) * 1000, 2)
    request.state.db_query_ms = query_duration_ms

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("", response_model=OrderResponse, status_code=201)
def create_order(order_in: OrderCreate, request: Request, db: Session = Depends(get_db)):
    query_start = time.perf_counter()
    user = db.query(User).filter(User.id == order_in.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    total = 0.0
    items_to_create = []

    for item_data in order_in.items:
        prod = db.query(Product).filter(Product.id == item_data.product_id).first()
        if not prod:
            raise HTTPException(status_code=400, detail=f"Product {item_data.product_id} not found")
        item_total = prod.price * item_data.quantity
        total += item_total
        items_to_create.append(
            OrderItem(product_id=prod.id, quantity=item_data.quantity, unit_price=prod.price)
        )

    order = Order(user_id=user.id, status="completed", total_amount=total)
    order.items = items_to_create
    db.add(order)
    db.commit()
    db.refresh(order)

    query_duration_ms = round((time.perf_counter() - query_start) * 1000, 2)
    request.state.db_query_ms = query_duration_ms

    return order
