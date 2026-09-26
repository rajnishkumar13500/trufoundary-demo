from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import datetime
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime.datetime

@router.get("", response_model=List[UserResponse])
def get_users(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(User).limit(limit).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("", response_model=UserResponse, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=user_in.name, email=user_in.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
