import enum
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class ColorMark(str, enum.Enum):
    none = "none"
    green = "green"
    yellow = "yellow"
    red = "red"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(50))
    mask = Column(String(50))
    gate = Column(String(50))
    login = Column(String(100))
    password_encrypted = Column(Text)  # AES-128 via Fernet
    teamviewer_id = Column(String(100))
    date = Column(Date)
    color_mark = Column(Enum(ColorMark), default=ColorMark.none)
    info_link = Column(String(500))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    ping_enabled = Column(Boolean, default=True)
    group_name = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    os_type = Column(String(100), nullable=True)
    server_type = Column(String(100), nullable=True)
    tags = Column(Text, default='[]')
    anydesk_id = Column(String(100), nullable=True)
    rudesktop_id = Column(String(100), nullable=True)
    preferred_vnc = Column(String(50), nullable=True)
    owner = Column(String(200), nullable=True)
    address = Column(String(500), nullable=True)
    provider = Column(String(200), nullable=True)
    contact_person = Column(String(200), nullable=True)
    access_groups = Column(Text, nullable=True)  # JSON array: ["Руководство", "Сотрудники"]

    created_by = relationship("User", foreign_keys=[created_by_id])
    history = relationship("ClientHistory", back_populates="client", cascade="all, delete-orphan")
