from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..models.user import UserRole


class UserBase(BaseModel):
    username: str
    role: UserRole = UserRole.user
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    avatar_color: Optional[str] = None
    user_group: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    avatar_color: Optional[str] = None
    user_group: Optional[str] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
