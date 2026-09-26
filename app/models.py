import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    orders = relationship("Order", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=100)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    # Notice: In the initial baseline, there is NO composite index on (user_id, created_at).
    # When querying: WHERE user_id = :uid ORDER BY created_at DESC
    # the database must perform a full scan or filesort across tens of thousands of records!
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="completed", nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
