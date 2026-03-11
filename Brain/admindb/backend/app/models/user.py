import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from ..database import Base


class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    full_name = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    telegram_username = Column(String(100), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True)
    avatar_color = Column(String(20), nullable=True, server_default='#1a4a2e')
    user_group = Column(String(100), nullable=True)  # "Руководство" | "Сотрудники"
