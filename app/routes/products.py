from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict
import datetime
from app.database import get_db
from app.models import Product

router = APIRouter(prefix="/products", tags=["products"])

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int = 100

class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    stock: int
    created_at: datetime.datetime

@router.get("", response_model=List[ProductResponse])
def get_products(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Product).limit(limit).all()

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    product = Product(name=product_in.name, price=product_in.price, stock=product_in.stock)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
