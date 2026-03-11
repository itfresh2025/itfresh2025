import enum
from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from ..database import Base


class RelationType(str, enum.Enum):
    duplicate = "duplicate"
    blocks = "blocks"
    related = "related"


class TicketRelation(Base):
    __tablename__ = "ticket_relations"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    related_ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    relation_type = Column(Enum(RelationType), default=RelationType.related)

    ticket = relationship("Ticket", foreign_keys=[ticket_id], back_populates="relations")
    related_ticket = relationship("Ticket", foreign_keys=[related_ticket_id])
