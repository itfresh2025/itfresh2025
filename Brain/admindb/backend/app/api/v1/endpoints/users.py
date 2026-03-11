from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ....database import get_db
from ....models.user import User
from ....schemas.user import UserCreate, UserUpdate, UserOut
from ....api.deps import get_current_user, require_admin
from ....core.security import get_password_hash

router = APIRouter()


@router.get("/", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(User).order_by(User.username).all()


@router.post("/", response_model=UserOut)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
    if user_in.username is not None:
        user.username = user_in.username
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.phone is not None:
        user.phone = user_in.phone
    if user_in.email is not None:
        user.email = user_in.email
    if user_in.telegram_username is not None:
        user.telegram_username = user_in.telegram_username
    if user_in.telegram_chat_id is not None:
        user.telegram_chat_id = user_in.telegram_chat_id
    if user_in.avatar_color is not None:
        user.avatar_color = user_in.avatar_color
    if user_in.user_group is not None:
        user.user_group = user_in.user_group

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}
