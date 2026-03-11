import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class TicketStatus(str, enum.Enum):
    new = "new"
    assigned = "assigned"
    in_progress = "in_progress"
    pending = "pending"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketSource(str, enum.Enum):
    manual = "manual"
    telegram = "telegram"
    zabbix = "zabbix"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TicketStatus), default=TicketStatus.new, nullable=False, index=True)
    priority = Column(Enum(TicketPriority), default=TicketPriority.medium, nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    pending_reason = Column(String(500), nullable=True)
    sla_paused = Column(Boolean, default=False)
    source = Column(Enum(TicketSource), default=TicketSource.manual, nullable=False)
    telegram_chat_id = Column(String(100), nullable=True)
    telegram_message_id = Column(String(100), nullable=True)
    notify_channel_id = Column(Integer, ForeignKey('notification_channels.id'), nullable=True)
    shared_fields = Column(Text, nullable=True, server_default='[]')

    client = relationship("Client", backref="tickets")
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    events = relationship("TicketEvent", back_populates="ticket", cascade="all, delete-orphan")
    relations = relationship(
        "TicketRelation",
        foreign_keys="TicketRelation.ticket_id",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
