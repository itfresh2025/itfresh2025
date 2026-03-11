import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class EventType(str, enum.Enum):
    created = "created"
    status_changed = "status_changed"
    priority_changed = "priority_changed"
    assigned = "assigned"
    comment_added = "comment_added"
    sla_breached = "sla_breached"
    closed = "closed"


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(Enum(EventType), nullable=False)
    old_value = Column(String(200), nullable=True)
    new_value = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="events")
    user = relationship("User", foreign_keys=[user_id])
