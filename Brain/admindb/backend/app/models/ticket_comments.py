from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    telegram_chat_id = Column(String(100), nullable=True)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])
