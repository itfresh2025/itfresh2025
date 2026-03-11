from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class PingHistory(Base):
    __tablename__ = "ping_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_online = Column(Boolean, nullable=False)
    response_ms = Column(Integer, nullable=True)

    client = relationship("Client", backref="ping_history")
