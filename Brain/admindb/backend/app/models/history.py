from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class ClientHistory(Base):
    __tablename__ = "client_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    action = Column(String(20))       # create / update / delete
    field_name = Column(String(100))  # which field changed
    old_value = Column(Text)
    new_value = Column(Text)

    client = relationship("Client", back_populates="history")
    changed_by = relationship("User")
