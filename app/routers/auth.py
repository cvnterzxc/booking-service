from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole
from app.schemas import UserCreate, UserRead
from app.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)) -> User:
    user = User(
        email=data.email,
        full_name=data.full_name,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=UserRole.client,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)
    return user